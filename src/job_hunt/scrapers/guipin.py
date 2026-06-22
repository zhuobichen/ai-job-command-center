"""
桂聘网 (guipin.com) 岗位抓取器
=============================
基于 httpx + BeautifulSoup，纯 HTML 解析，必要时用 browser-act。

网站结构（2024版）：
- 搜索页: https://www.guipin.com/search/?keyword={kw}&page={n}
- 详情页: https://www.guipin.com/job/{id}.html
"""

import time
import re
from typing import List, Optional
from urllib.parse import quote

from ..models.job import Job
from .base import BaseScraper
from .gxrc import GX_CITY_KEYWORDS, GD_CITY_KEYWORDS


class GuiPinScaper(BaseScraper):
    """桂聘网抓取器"""

    platform: str = "guipin"
    name: str = "桂聘网"
    base_url: str = "https://www.guipin.com"

    def search(
        self,
        keyword: str,
        city: str = "",
        max_pages: int = 3,
        delay: float = 1.5,
    ) -> List[Job]:
        """搜索岗位"""
        jobs: List[Job] = []

        for page in range(1, max_pages + 1):
            url = self._build_search_url(keyword, page)
            soup = self._get(url)
            if not soup:
                print(f"  [guipin] 第{page}页请求失败")
                break

            cards = self._parse_job_cards(
                soup,
                selectors=[
                    "li.job-item",
                    "div.job-list-item",
                    "div.position-card",
                    "div.search-result-item",
                    "div.job-info-box",
                ],
            )
            if not cards:
                # 降级：找所有包含岗位信息的链接
                cards = soup.select(
                    "a[href*='/job/'], a[href*='/detail/'], a[href*='/position/']"
                )
                # 过滤太短或太泛的链接
                cards = [
                    c for c in cards
                    if len(c.get_text(strip=True)) > 5
                    and "首页" not in c.get_text()
                ]

            if not cards:
                if self.debug:
                    self._save_debug_html(url, str(soup))
                break

            for card in cards:
                try:
                    job = self._parse_card(card)
                    if job and job.title:
                        if city and not self._match_city(job.city, city):
                            continue
                        jobs.append(job)
                except Exception as e:
                    if self.debug:
                        print(f"  [guipin] 解析出错: {e}")
                    continue

            print(f"  [guipin] 第{page}页 已收集 {len(jobs)} 个岗位")

            if not self._has_next_page(soup):
                break
            if page < max_pages:
                time.sleep(delay)

        return jobs

    # ------------------------------------------------------------------
    def _build_search_url(self, keyword: str, page: int) -> str:
        kw = quote(keyword.strip())
        return f"{self.base_url}/search/?keyword={kw}&page={page}"

    # ------------------------------------------------------------------
    def _has_next_page(self, soup) -> bool:
        next_el = soup.select_one(
            "a.next:not(.disabled), .pagination .next:not(.disabled), "
            "li.next a, a[rel='next']"
        )
        if next_el:
            return True
        # 检查是否有 "下一页" 文本链接
        for a in soup.select("a"):
            if "下一页" in a.get_text():
                return True
        return False

    # ------------------------------------------------------------------
    def _parse_card(self, card) -> Optional[Job]:
        job = Job(platform=self.platform)

        # 标题 + 链接（优先 a 标签）
        if card.name == "a":
            title_el = card
        else:
            title_el = card.select_one(
                "a.job-name, a.position-title, a.job-title, h3 a, h4 a, "
                "span.job-name a, .title a"
            )
            if not title_el:
                title_el = card.select_one("a[href*='/job/']")

        if title_el and title_el.name == "a":
            job.title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            if href:
                job.source_url = (
                    href if href.startswith("http")
                    else f"{self.base_url}{href}" if href.startswith("/")
                    else f"{self.base_url}/{href}"
                )
        else:
            job.title = card.get_text(" ", strip=True)[:80]

        if not job.title or len(job.title) < 3:
            return None

        # 公司
        company_el = card.select_one(
            "a.company-name, span.company, div.company, .corp-name, "
            "a[href*='/company/'], a[href*='/corp/']"
        )
        if company_el:
            job.company = company_el.get_text(strip=True)

        # 城市
        city_el = card.select_one(
            "span.city, span.location, span.job-city, .work-place, span.area"
        )
        if city_el:
            job.city = city_el.get_text(strip=True)
        else:
            job.city = self._extract_city(card.get_text(" ", strip=True))

        # 薪资
        salary_el = card.select_one(
            "span.salary, span.pay, span.job-salary, .salary, .money"
        )
        if salary_el:
            job.salary_text = salary_el.get_text(strip=True)
            self._parse_salary(job, job.salary_text)

        # 学历/经验
        full_text = card.get_text(" ", strip=True)
        for w in ["本科", "硕士", "博士", "大专", "学历不限"]:
            if w in full_text and not job.education:
                job.education = w

        exp_match = re.search(r'(\d+年|应届|经验不限)', full_text)
        if exp_match and not job.experience:
            job.experience = exp_match.group(1)

        return job

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_city(text: str) -> str:
        all_cities = GX_CITY_KEYWORDS + GD_CITY_KEYWORDS
        for city in sorted(all_cities, key=len, reverse=True):
            if city in text:
                return city
        return ""

    # ------------------------------------------------------------------
    @staticmethod
    def _match_city(job_city: str, target: str) -> bool:
        if not target or not job_city:
            return True
        targets = [t.strip() for t in target.split(",")]
        job_lower = job_city.lower()
        for t in targets:
            if t.lower() in job_lower or job_lower in t.lower():
                return True
        return False

    # ------------------------------------------------------------------
    @staticmethod
    def _parse_salary(job: Job, text: str) -> None:
        text = text.strip().upper().replace(" ", "")
        match = re.search(r'(\d+)\s*[Kk千]\s*[-~—]\s*(\d+)\s*[Kk千]', text)
        if match:
            job.salary_min = int(match.group(1)) * 1000
            job.salary_max = int(match.group(2)) * 1000
            return
        match = re.search(r'(\d{4,6})\s*[-~—]\s*(\d{4,6})', text)
        if match:
            job.salary_min = int(match.group(1))
            job.salary_max = int(match.group(2))
