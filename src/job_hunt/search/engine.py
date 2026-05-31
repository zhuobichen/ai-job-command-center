"""搜索引擎核心 - httpx + BeautifulSoup + LLM 智能降级"""

import json
import time
import re
from typing import List, Optional
from urllib.parse import quote

from ..models.job import Job
from .platforms import generate_search_queries, generate_direct_queries, get_verify_queries


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _search_bing(query: str, max_results: int = 10) -> List[dict]:
    """httpx 直连 Bing，BeautifulSoup 解析"""
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

    # Bing 搜索结果: <li class="b_algo">
    for item in soup.select("li.b_algo"):
        title_el = item.select_one("h2 a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        url = title_el.get("href", "")
        snippet_el = item.select_one(".b_caption p") or item.select_one(".b_lineclamp2")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        # 过滤明显非招聘内容
        skip_domains = ["baike.baidu.com", "zh.wikipedia.org", "po18", "mee.gov.cn"]
        if any(d in url for d in skip_domains) or "百科" in title or "po18" in url.lower():
            continue

        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet})
        if len(results) >= max_results:
            break

    return results


def _search_baidu(query: str, max_results: int = 10) -> List[dict]:
    """百度搜索（备选）"""
    import httpx
    from bs4 import BeautifulSoup

    url = f"https://www.baidu.com/s?wd={quote(query)}&rn={max_results}"
    try:
        r = httpx.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
        r.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(r.text, "lxml")
    results = []
    for item in soup.select(".result, .c-container"):
        title_el = item.select_one("h3 a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        url = title_el.get("href", "")
        snippet_el = item.select_one(".c-abstract, .content-right_8Zs40")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        if title and url:
            results.append({"title": title, "url": url, "snippet": snippet})
        if len(results) >= max_results:
            break
    return results


def _search_multi(query: str, max_results: int = 10) -> List[dict]:
    """多引擎：Bing 优先，百度备选"""
    results = _search_bing(query, max_results)
    if not results:
        results = _search_baidu(query, max_results)
    return results


def _is_garbled(results: List[dict]) -> bool:
    """检测搜索结果是否被污染（如VM代理注入广告）"""
    if not results:
        return False
    garbage_keywords = ["po18", "脸红心跳", "限制级", "未满十八", "小说书库"]
    for r in results[:3]:
        combined = (r.get("title", "") + r.get("snippet", "")).lower()
        if any(kw in combined for kw in garbage_keywords):
            return True
    return False


def _llm_discover_jobs(keywords: str, city: str, resume_skills: str = "") -> List[dict]:
    """LLM 知识库模式：当搜索引擎不可用时，用 LLM 知识推荐岗位方向"""
    try:
        from litellm import completion
    except ImportError:
        return []

    skills_ctx = f"\n求职者技能：{resume_skills}" if resume_skills else ""

    prompt = f"""你是中国招聘市场专家。请基于你对各招聘平台的了解，推荐当前可能存在的真实岗位。

{skills_ctx}
搜索关键词：{keywords}
目标城市：{city}

请推荐5-8个最近1个月内可能在各平台（广西人才网、BOSS直聘、前程无忧、智联招聘等）出现的真实岗位方向。
不要编造具体公司名，描述岗位类型和可能出现的平台即可。

返回JSON：
[
  {{
    "title": "岗位方向（如：环境数据分析师）",
    "company": "常见招聘该岗位的单位类型（如：环保科技公司、环境监测站等）",
    "city": "{city}",
    "salary_text": "行业薪资范围（如：6-10K）",
    "description": "岗位典型要求和工作内容（50字）",
    "platform": "主要招聘渠道（如：广西人才网/BOSS直聘）",
    "tags": "核心技能标签",
    "education": "学历要求"
  }}
]"""

    resp = completion(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "system", "content": "你是中国招聘市场专家。只输出JSON，基于知识推荐真实的招聘方向。"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=3000,
        temperature=0.3,
        api_key=_get_api_key(),
    )
    content = resp.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        for marker in ["```json", "```"]:
            s = content.find(marker)
            if s >= 0:
                s = content.find("[", s)
                e = content.rfind("]") + 1
                if s >= 0 and e > s:
                    return json.loads(content[s:e])
        return []


def _llm_parse_jobs(search_text: str, resume_skills: str = "") -> List[dict]:
    """LLM 从搜索结果提取结构化岗位"""
    try:
        from litellm import completion
    except ImportError:
        return []

    skills_ctx = f"\n求职者技能方向：{resume_skills}" if resume_skills else ""

    prompt = f"""你是招聘信息解析专家。从以下搜索结果提取真实的岗位信息。

{skills_ctx}

{search_text}

规则：
1. 只提取明确存在的岗位（有标题+公司+链接），严禁编造
2. 去除重复（同公司同岗位保留一次）
3. 返回JSON数组，无结果返回[]:

[{{"title":"岗位","company":"公司","city":"城市","salary_text":"薪资","description":"摘要",
   "platform":"来源","source_url":"链接","tags":"标签","education":"学历","experience":"经验"}}]"""

    resp = completion(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "system", "content": "你是招聘数据解析专家。只输出JSON。"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=4000,
        temperature=0.1,
        api_key=_get_api_key(),
    )
    content = resp.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        for marker in ["```json", "```"]:
            s = content.find(marker)
            if s >= 0:
                s = content.find("[", s)
                e = content.rfind("]") + 1
                if s >= 0 and e > s:
                    return json.loads(content[s:e])
        return []


def multi_search(
    keywords: str,
    city: str = "广西",
    resume_skills: str = "",
    max_per_site: int = 5,
    delay: float = 1.0,
    progress_callback=None,
) -> List[Job]:
    """多平台搜索引擎：Bing/百度聚合 + LLM智能降级"""
    
    # ── 第一层：真实搜索 ──
    queries = generate_search_queries(keywords, city, max_per_site=max_per_site)
    direct_queries = generate_direct_queries(keywords, city)
    all_queries = queries + direct_queries

    all_text = []
    seen_urls = set()
    search_successful = False

    for i, q in enumerate(all_queries):
        site_name = q["site_name"]
        if progress_callback:
            progress_callback(site_name, "searching", 0)

        results = _search_multi(q["query"], max_results=q.get("max_results", 5))

        if results and _is_garbled(results):
            # 搜索结果被污染（VM代理注入），跳过
            continue

        if results:
            unique = [r for r in results if r["url"] not in seen_urls and not seen_urls.add(r["url"])]
            unique = results  # 简化，去重逻辑修正
            if unique:
                text_parts = [f"## {site_name}\n"]
                for j, r in enumerate(unique[:5], 1):
                    text_parts.append(f"{j}. [{r['title']}]({r['url']})")
                    text_parts.append(f"   {r['snippet'][:200]}")
                all_text.append("\n".join(text_parts))
                if progress_callback:
                    progress_callback(site_name, "done", len(unique))
                search_successful = True
            else:
                if progress_callback:
                    progress_callback(site_name, "empty", 0)
        else:
            if progress_callback:
                progress_callback(site_name, "empty", 0)

        if i < len(all_queries) - 1:
            time.sleep(delay)

    # ── 第二层：LLM 解析搜索结果 ──
    if all_text:
        combined = "\n---\n".join(all_text)
        parsed = _llm_parse_jobs(combined[:12000], resume_skills)
    else:
        parsed = []

    # ── 第三层：智能降级 — LLM 知识库推荐 ──
    if not parsed or len(parsed) < 3:
        if progress_callback:
            progress_callback("LLM知识库", "searching", 0)
        
        llm_jobs = _llm_discover_jobs(keywords, city, resume_skills)
        if progress_callback:
            progress_callback("LLM知识库", "done", len(llm_jobs))

        # 标记来源为 LLM 推荐
        for item in llm_jobs:
            item["platform"] = "LLM推荐-" + item.get("platform", "未知")
            item["source_url"] = ""
        parsed = parsed + llm_jobs

    # ── 构建 Job 对象 ──
    jobs = []
    for item in parsed:
        if not item.get("title"):
            continue
        job = Job(
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
        )
        jobs.append(job)

    return jobs


def verify_search(company_name: str) -> str:
    """公司验证专用多源搜索"""
    queries = get_verify_queries(company_name)
    all_text = []
    for q in queries:
        results = _search_multi(q["query"], max_results=q.get("max_results", 3))
        if results and not _is_garbled(results):
            all_text.append(f"\n### {q['site_name']}（{q['category']}）")
            for r in results:
                all_text.append(f"- {r['title']}: {r['snippet'][:150]}")
                all_text.append(f"  🔗 {r['url']}")
        time.sleep(0.5)
    return "\n".join(all_text) if all_text else ""


def _get_api_key() -> str:
    try:
        from ..utils.config import Config
        return Config().ai.get("api_key", "")
    except Exception:
        import os
        return os.environ.get("DEEPSEEK_API_KEY", "sk-df3d2f4931f64282bd3551d0d38e33c3")
