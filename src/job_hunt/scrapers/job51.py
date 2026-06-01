"""前程无忧 (51job.com) 抓取器

51job 有新旧两版：
- 旧版 search.51job.com（服务端渲染，首选）
- 新版 we.51job.com（SPA，需要分析 API）
"""

import re
import time
from typing import List, Optional
from urllib.parse import quote

from .base import BaseScraper, HEADERS
from ..models.job import Job


class Job51Scraper(BaseScraper):
    """前程无忧抓取器"""

    platform = "job51"
    name = "前程无忧"
    base_url = "https://search.51job.com"

    def search(
        self,
        keyword: str,
        city: str = "",
        max_pages: int = 3,
        delay: float = 2.0,
    ) -> List[Job]:
        jobs: List[Job] = []

        for page in range(1, max_pages + 1):
            url = self._build_search_url(keyword, city, page)
            soup = self._get(url)
            if not soup:
                # 旧版失败尝试新版
                soup = self._try_new_version(keyword, city, page)

            if not soup:
                break

            cards = self._find_cards(soup)
            if not cards:
                break

            for card in cards:
                job = self._parse_card(card)
                if job and job.title:
                    jobs.append(job)

            if page < max_pages:
                time.sleep(delay)

        return jobs

    def _build_search_url(self, keyword: str, city: str = "", page: int = 1) -> str:
        """旧版搜索 URL"""
        url = f"{self.base_url}/list/000000,000000,0000,00,9,99,{quote(keyword)},2,{page}.html"
        if city:
            # 旧版通过 location 参数过滤
            url += f"?location={quote(city)}"
        return url

    def _try_new_version(self, keyword: str, city: str = "", page: int = 1):
        """新版搜索（we.51job.com 返回 JSON API）"""
        try:
            url = "https://we.51job.com/api/job/search-pc"
            params = {
                "keyword": keyword,
                "location": city,
                "pageNum": str(page),
                "pageSize": "20",
            }
            r = self.client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            # 新版返回 JSON，用 _parse_api_results 处理
            self._api_results = data
            return None  # 标记使用 API 模式
        except Exception:
            return None

    def _find_cards(self, soup) -> List:
        """查找岗位卡片"""
        strategies = [
            "div.el > div.joblist > div.e",
            "div.jlist > div.e",
            "div#resultList div.el",
            "div.rl_item", "div.job_item",
            "[class*='joblist'] > div[class*='e']",
        ]
        for sel in strategies:
            cards = soup.select(sel)
            if len(cards) > 1:
                return cards
        return []

    def _parse_card(self, card) -> Optional[Job]:
        job = Job(platform=self.platform)

        # 51job 旧版结构：
        # <div class="el">
        #   <p class="t1"><span><a>职位名</a></span></p>
        #   <span class="t2"><a>公司名</a></span>
        #   <span class="t3">工作地点</span>
        #   <span class="t4">薪资</span>
        #   <span class="t5">发布日期</span>

        # 标题
        title_selectors = ["p.t1 a", "span.t1 a", ".job_name a", "a.title", "a[href*='job']"]
        for sel in title_selectors:
            a = card.select_one(sel)
            if a and a.get_text(strip=True):
                job.title = a.get_text(strip=True)
                href = a.get("href", "")
                job.source_url = href if href.startswith("http") else f"https://jobs.51job.com{href}" if href.startswith("/") else href
                break

        if not job.title:
            for a in card.select("a"):
                text = a.get_text(strip=True)
                if len(text) >= 4:
                    job.title = text
                    href = a.get("href", "")
                    job.source_url = href
                    break

        # 公司
        company_selectors = ["span.t2 a", "p.t2 a", ".company a", "a.cname"]
        for sel in company_selectors:
            c = card.select_one(sel)
            if c:
                job.company = c.get_text(strip=True)
                break

        # 城市
        city_selectors = ["span.t3", ".location", ".work_place"]
        for sel in city_selectors:
            c = card.select_one(sel)
            if c:
                job.city = c.get_text(strip=True)[:20]
                break

        # 薪资
        salary_selectors = ["span.t4", ".salary", ".pay"]
        for sel in salary_selectors:
            s = card.select_one(sel)
            if s:
                job.salary_text = s.get_text(strip=True)
                self._parse_salary(job, job.salary_text)
                break

        # 日期
        date_selectors = ["span.t5", ".date", ".time"]
        for sel in date_selectors:
            d = card.select_one(sel)
            if d:
                job.created_at = d.get_text(strip=True)
                break

        return job

    def _parse_salary(self, job: Job, text: str):
        text = text.replace("万/年", "0000/年").replace("/年", "").replace("千/月", "000/月").replace("/月", "")
        nums = re.findall(r"(\d+\.?\d*)", text)
        if len(nums) >= 2:
            lo, hi = float(nums[0]), float(nums[1])
            if "年" in text:
                lo, hi = lo / 12, hi / 12
            elif "万" in text:
                lo, hi = lo * 10000, hi * 10000
            elif lo < 50:
                lo, hi = lo * 1000, hi * 1000
            job.salary_min, job.salary_max = int(lo), int(hi)
