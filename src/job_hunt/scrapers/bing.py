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
    """
    client = httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True)
    jobs: List[Job] = []

    queries = [
        f'"{keyword}" {city} 招聘 site:gxrc.com',
        f'"{keyword}" {city} 招聘 site:51job.com',
        f'"{keyword}" {city} 招聘 site:zhaopin.com',
    ]

    try:
        for query in queries:
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
                snippet_el = item.select_one(".b_caption p") or item.select_one(".b_lineclamp2")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                # 过滤无关内容
                skip_keywords = ["baike", "百科", "wiki", "举报", "投诉"]
                if any(k in title + snippet for k in skip_keywords):
                    continue

                # 尝试从摘要提取薪资和城市
                salary_text = ""
                sal_match = re.search(r"(\d+[Kk千]-?\d*[Kk千]?)", snippet)
                if sal_match:
                    salary_text = sal_match.group(1)

                card_city = city[:2] if city else ""
                city_match = re.search(
                    r"(南宁|柳州|桂林|梧州|北海|防城港|钦州|贵港|玉林|百色|贺州|河池|来宾|崇左)",
                    snippet + title,
                )
                if city_match:
                    card_city = city_match.group(1)

                jobs.append(Job(
                    title=title,
                    company="",  # 摘要中通常没有公司名
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
