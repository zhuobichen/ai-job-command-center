"""搜索引擎 - 双模架构

模式1 (Standalone): httpx 直连 Bing 搜索，BeautifulSoup 解析
模式2 (Agent): 外部 Agent 通过 WebSearch 工具搜索，结果写入 JSON 文件导入

设计原则：
- 不做 JS 渲染抓取（招聘网站几乎都是 SPA）
- 不做 API 鉴权破解（容易被封）
- 搜索引擎 + LLM 解析 = 最稳定方案
"""

import json
import time
import os
import re
from typing import List, Optional, Callable
from urllib.parse import quote

from ..models.job import Job
from .platforms import generate_search_queries, generate_direct_queries, get_verify_queries

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# ─── 底层搜索 ────────────────────────────────────────────

def _bing_html(query: str, max_results: int = 10) -> List[dict]:
    """Bing HTML 搜索（httpx + bs4）"""
    import httpx
    from bs4 import BeautifulSoup

    url = f"https://www.bing.com/search?q={quote(query)}&count={max_results}"
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        r.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(r.text, "lxml")
    results = []
    skip_domains = {"baike.baidu.com", "wikipedia.org", "po18", "mee.gov.cn", "cenews.com.cn"}

    for item in soup.select("li.b_algo"):
        title_el = item.select_one("h2 a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        snippet_el = item.select_one(".b_caption p") or item.select_one(".b_lineclamp2")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        if any(d in href for d in skip_domains):
            continue
        if title and href:
            results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def _baidu_html(query: str, max_results: int = 10) -> List[dict]:
    """百度搜索（备选）"""
    import httpx
    from bs4 import BeautifulSoup

    url = f"https://www.baidu.com/s?wd={quote(query)}&rn={max_results}"
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        r.raise_for_status()
    except Exception:
        return []

    if "captcha" in r.url or "wappass" in r.url:
        return []  # 验证码

    soup = BeautifulSoup(r.text, "lxml")
    results = []
    for item in soup.select(".result, .c-container"):
        title_el = item.select_one("h3 a")
        if not title_el:
            continue
        results.append({
            "title": title_el.get_text(strip=True),
            "url": title_el.get("href", ""),
            "snippet": (item.select_one(".c-abstract") or title_el).get_text(strip=True),
        })
        if len(results) >= max_results:
            break
    return results


def search_web(query: str, max_results: int = 10) -> List[dict]:
    """统一搜索入口：Bing → 百度"""
    r = _bing_html(query, max_results)
    if not r:
        r = _baidu_html(query, max_results)
    return r


# ─── LLM 解析 ────────────────────────────────────────────

def _llm_parse(text: str, skills: str = "") -> List[dict]:
    """LLM 从文本中提取招聘岗位"""
    try:
        from litellm import completion
    except ImportError:
        return []

    sk = f"\n求职者：{skills}" if skills else ""
    prompt = f"""你从搜索结果提取真实招聘岗位。只输出JSON，不编造。无结果输出[]。

{sk}

{text}

格式: [{{"title":"岗位","company":"公司","city":"城市","salary_text":"薪资",
"description":"摘要","platform":"来源","source_url":"链接","tags":"标签",
"education":"学历","experience":"经验"}}]"""

    resp = completion(
        model="deepseek/deepseek-chat",
        messages=[{"role": "system", "content": "只输出JSON，不编造数据"}, {"role": "user", "content": prompt}],
        max_tokens=4000, temperature=0.1, api_key=_api_key(),
    )
    raw = resp.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("["), raw.rfind("]") + 1
        return json.loads(raw[s:e]) if s >= 0 and e > s else []


def _llm_discover(keywords: str, city: str, skills: str = "") -> List[dict]:
    """LLM 知识库推荐（搜索引擎不可用时的降级）"""
    try:
        from litellm import completion
    except ImportError:
        return []

    prompt = f"""推荐5-8个{city}地区"{keywords}"方向的真实岗位方向。
描述岗位类型、典型雇主、薪资范围、主要招聘渠道。
返回JSON: [{{"title":"岗位方向","company":"雇主类型","city":"{city}",
"salary_text":"薪资","description":"50字","platform":"渠道","tags":"技能","education":"学历"}}]"""

    resp = completion(
        model="deepseek/deepseek-chat",
        messages=[{"role": "system", "content": "只输出JSON"}, {"role": "user", "content": prompt}],
        max_tokens=3000, temperature=0.3, api_key=_api_key(),
    )
    raw = resp.choices[0].message.content.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        s, e = raw.find("["), raw.rfind("]") + 1
        return json.loads(raw[s:e]) if s >= 0 and e > s else []


# ─── 多源搜索 ────────────────────────────────────────────

def multi_search(
    keywords: str, city: str = "广西", resume_skills: str = "",
    max_per_site: int = 5, delay: float = 0.8,
    progress: Optional[Callable] = None,
) -> List[Job]:
    """多源搜索引擎 - 双模架构"""
    queries = generate_search_queries(keywords, city, max_per_site=max_per_site)
    all_queries = queries + generate_direct_queries(keywords, city)
    
    all_text = []
    total_results = 0
    
    for i, q in enumerate(all_queries):
        if progress:
            progress(q["site_name"], "searching", 0)
        
        results = search_web(q["query"], max_results=q.get("max_results", 5))
        
        if results:
            total_results += len(results)
            lines = [f"## {q['site_name']}\n"]
            for j, r in enumerate(results[:5], 1):
                lines.append(f"{j}. [{r['title']}]({r['url']})")
                lines.append(f"   {r['snippet'][:200]}")
            all_text.append("\n".join(lines))
            if progress:
                progress(q["site_name"], "done", len(results))
        else:
            if progress:
                progress(q["site_name"], "empty", 0)
        
        if i < len(all_queries) - 1:
            time.sleep(delay)
    
    # LLM 解析
    parsed = _llm_parse("\n---\n".join(all_text)[:12000], resume_skills) if all_text else []
    
    # 降级
    if not parsed or len(parsed) < 3:
        if progress:
            progress("LLM知识库", "searching", 0)
        llm_jobs = _llm_discover(keywords, city, resume_skills)
        for item in llm_jobs:
            item["platform"] = "LLM推荐-" + item.get("platform", "")
            item["source_url"] = ""
        if progress:
            progress("LLM知识库", "done", len(llm_jobs))
        parsed += llm_jobs
    
    # 构建 Job
    jobs = []
    for item in parsed:
        if not item.get("title"):
            continue
        jobs.append(Job(
            title=item.get("title", ""),
            company=item.get("company", ""),
            city=item.get("city", city),
            salary_text=item.get("salary_text", "面议"),
            description=item.get("description", ""),
            platform=item.get("platform", "web"),
            source_url=item.get("source_url", ""),
            tags=item.get("tags", ""),
            education=item.get("education", ""),
            experience=item.get("experience", ""),
        ))
    return jobs


def verify_search(company_name: str) -> str:
    """公司验证搜索"""
    lines = []
    for q in get_verify_queries(company_name):
        results = search_web(q["query"], q.get("max_results", 3))
        if results:
            lines.append(f"\n### {q['site_name']}")
            for r in results:
                lines.append(f"- {r['title']}: {r['snippet'][:150]}\n  {r['url']}")
        time.sleep(0.5)
    return "\n".join(lines)


# ─── Agent 导入模式 ───────────────────────────────────────

def import_from_agent(results: List[dict]) -> List[Job]:
    """Agent 模式：接收外部 WebSearch 结果并解析
    
    results: [{"title":"...", "url":"...", "snippet":"..."}, ...]
    """
    text = "\n".join(f"{i}. [{r['title']}]({r['url']})\n   {r.get('snippet','')}" 
                     for i, r in enumerate(results, 1))
    parsed = _llm_parse(text[:12000], "")
    
    jobs = []
    for item in parsed:
        if not item.get("title"):
            continue
        jobs.append(Job(
            title=item.get("title", ""),
            company=item.get("company", ""),
            city=item.get("city", ""),
            salary_text=item.get("salary_text", "面议"),
            description=item.get("description", ""),
            platform=item.get("platform", "web"),
            source_url=item.get("source_url", ""),
            tags=item.get("tags", ""),
            education=item.get("education", ""),
            experience=item.get("experience", ""),
        ))
    return jobs


def _api_key() -> str:
    """获取 API Key，优先级：配置 > 环境变量 > 硬编码"""
    import os
    # 尝试从配置文件加载
    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "config.toml")
        config_path = os.path.abspath(config_path)
        if os.path.exists(config_path):
            import tomli
            with open(config_path, "rb") as f:
                data = tomli.load(f)
                key = data.get("ai", {}).get("api_key", "")
                if key and key != "your-api-key-here":
                    return key
    except Exception:
        pass
    # 环境变量
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key:
        return key
    # 回退（仅开发用）
    return "sk-df3d2f4931f64282bd3551d0d38e33c3"
