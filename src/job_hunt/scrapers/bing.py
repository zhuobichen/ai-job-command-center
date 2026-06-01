"""Bing 搜索引擎抓取 — 补充渠道

直接从 Bing 搜索结果发现招聘信息（不上招聘网站反爬名单），
提取链接后可选深入抓取详情页。
"""

import re
import time
from typing import List
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from ..models.job import Job
from .base import HEADERS


def bing_job_search(
    keyword: str, city: str = "广西", max_results: int = 15, delay: float = 1.0
) -> List[Job]:
    """Bing 搜索发现岗位（通用引擎，不上招聘网站反爬名单）

    通过 site: 限定 + 招聘关键词在 Bing 搜索，提取搜索结果中的链接。
    结果不进入招聘网站爬虫，只从搜索结果摘要提取基本信息。
    
    增强版特性：
    - 关键词变体扩展
    - 多站点并行搜索
    - 智能过滤和去重
    """
    client = httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True)
    jobs: List[Job] = []
    seen_urls = set()

    queries = _build_queries(keyword, city)

    try:
        for query_info in queries:
            query = query_info["query"]
            site_name = query_info["site_name"]
            url = f"https://www.bing.com/search?q={quote(query)}&count={max_results}"
            try:
                r = client.get(url)
                r.raise_for_status()
            except Exception:
                continue

            soup = BeautifulSoup(r.text, "lxml")
            for item in soup.select("li.b_algo"):
                title_el = item.select_one("h2 a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                
                # 去重
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                snippet_el = item.select_one(".b_caption p") or item.select_one(".b_lineclamp2")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                # 过滤无关内容
                if _should_skip(title, snippet):
                    continue

                # 提取公司名
                company = _extract_company(title, snippet)

                # 提取薪资
                salary_text = _extract_salary(snippet)

                # 提取城市
                card_city = _extract_city(city, title, snippet)

                jobs.append(Job(
                    title=title,
                    company=company,
                    city=card_city,
                    salary_text=salary_text,
                    description=snippet[:500],
                    platform="bing",
                    source_url=href,
                    tags=keyword,
                ))

            time.sleep(delay)

    finally:
        client.close()

    return jobs


def _build_queries(keyword: str, city: str) -> List[dict]:
    """构建增强型搜索查询列表"""
    queries = []
    
    sites = [
        {"domain": "gxrc.com", "name": "广西人才网"},
        {"domain": "51job.com", "name": "前程无忧"},
        {"domain": "zhaopin.com", "name": "智联招聘"},
        {"domain": "zhipin.com", "name": "BOSS直聘"},
        {"domain": "liepin.com", "name": "猎聘"},
        {"domain": "gov.cn", "name": "政府事业单位"},
        {"domain": "edu.cn", "name": "高校就业"},
    ]
    
    keyword_variants = _get_keyword_variants(keyword)
    
    for site in sites:
        for variant in keyword_variants:
            queries.append({
                "query": f'"{variant}" {city} 招聘 site:{site["domain"]}',
                "site_name": site["name"],
            })
    
    return queries


def _get_keyword_variants(keyword: str) -> List[str]:
    """生成关键词变体"""
    variants = [keyword]
    
    mappings = {
        "环境信息系统": ["环境信息化", "环保信息化", "环境数据"],
        "数据分析": ["数据分析师", "数据挖掘", "BI分析"],
        "GIS": ["地理信息系统", "空间分析"],
        "工程师": ["开发", "技术"],
        "环保": ["环境保护", "生态环境"],
    }
    
    for k, v in mappings.items():
        if k in keyword:
            variants.extend(v)
    
    return list(set(variants))


def _should_skip(title: str, snippet: str) -> bool:
    """判断是否应该跳过此结果"""
    skip_patterns = [
        "baike", "百科", "wiki", "举报", "投诉", "广告",
        "百度快照", "360快照", "微博", "论坛", "博客",
        "培训", "课程", "教育", "招聘信息",
    ]
    text = (title + snippet).lower()
    return any(pattern in text for pattern in skip_patterns)


def _extract_company(title: str, snippet: str) -> str:
    """从标题和摘要中提取公司名"""
    patterns = [
        r"([\u4e00-\u9fa5]{2,20})招聘",
        r"招聘.*?([\u4e00-\u9fa5]{2,20})",
    ]
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return match.group(1)
    return ""


def _extract_salary(snippet: str) -> str:
    """从摘要中提取薪资信息"""
    patterns = [
        r"(\d+[Kk千][-_~]?\d*[Kk千]?)",
        r"(\d+[Kk])-(\d+[Kk])",
        r"薪资(\d+-\d+)[Kk]",
    ]
    for pattern in patterns:
        match = re.search(pattern, snippet)
        if match:
            return match.group(1) if len(match.groups()) == 1 else f"{match.group(1)}-{match.group(2)}"
    return ""


def _extract_city(default_city: str, title: str, snippet: str) -> str:
    """提取城市信息"""
    cities = ["南宁", "柳州", "桂林", "梧州", "北海", "防城港", 
              "钦州", "贵港", "玉林", "百色", "贺州", "河池", "来宾", "崇左"]
    text = title + snippet
    for city in cities:
        if city in text:
            return city
    return default_city[:2] if default_city else ""
