"""广西人才网 (gxrc.com) 抓取器 — Playwright 浏览器模式

gxrc.com 是 SPA（Vue.js），需要浏览器渲染。
搜索入口: https://s.gxrc.com/sJob?keyword=xxx
"""

import asyncio
import re
import time
from typing import List

from ..models.job import Job
from ..utils.display import print_status, print_info, print_success, print_warning


class GxrcScraper:
    """广西人才网 Playwright 抓取器"""

    PLATFORM = "gxrc"
    BASE_URL = "https://s.gxrc.com"
    SEARCH_URL = f"{BASE_URL}/sJob"

    def __init__(self, headless: bool = True, debug: bool = False):
        self.headless = headless
        self.debug = debug
        self.browser = None
        self.context = None

    async def _init_browser(self):
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError("需要安装 playwright: pip install playwright && playwright install chromium")

        self._pw = await async_playwright().start()
        self.browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

    async def close(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, "_pw"):
            await self._pw.stop()

    async def search(
        self,
        keyword: str,
        city: str = "",
        max_pages: int = 3,
        delay: float = 2.0,
    ) -> List[Job]:
        """搜索岗位"""
        import urllib.parse

        print_status(f"🔍 广西人才网 | 搜索: {keyword} | 城市: {city or '全国'}")

        await self._init_browser()
        page = await self.context.new_page()
        jobs: List[Job] = []

        try:
            # 构建搜索URL
            params = {"keyword": keyword}
            if city:
                params["city"] = city
            query = urllib.parse.urlencode(params)
            search_url = f"{self.SEARCH_URL}?{query}"

            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(delay)

            # 检查页面是否正常加载
            title = await page.title()
            if "javascript" in title.lower() or "sorry" in title.lower():
                print_warning("广西人才网需要JS渲染，页面可能未正常加载")
                if self.debug:
                    await page.screenshot(path="logs/gxrc_debug.png")
                return jobs

            for p in range(max_pages):
                print_status(f"抓取第 {p + 1} 页...")
                await asyncio.sleep(delay)

                # GXRC 真实DOM结构: div.position-item > div.position-item-body > a.position-item-left
                job_cards = await page.query_selector_all("div.position-item")
                if not job_cards:
                    job_cards = await page.query_selector_all("div.search-position-list > div")
                if not job_cards:
                    # 截图调试
                    if self.debug:
                        await page.screenshot(path=f"logs/gxrc_page{p}.png")
                        html = await page.content()
                        with open(f"logs/gxrc_page{p}.html", "w", encoding="utf-8") as f:
                            f.write(html[:50000])
                    print_warning(f"第{p+1}页未找到岗位卡片(.position-item)，已保存调试截图")
                    break

                for card in job_cards:
                    try:
                        job = await self._parse_card(card)
                        if job and job.title:
                            jobs.append(job)
                    except Exception:
                        continue

                print_info(f"本页抓取 {len(job_cards)} 个岗位")

                # 翻页（Element UI 分页器）
                if p < max_pages - 1:
                    try:
                        # GXRC 使用 Element UI 分页: button.btn-next
                        next_btn = await page.query_selector("button.btn-next:not([disabled])")
                        if not next_btn:
                            next_btn = await page.query_selector(".el-pagination button:last-child:not([disabled])")
                        if not next_btn:
                            next_btn = await page.query_selector("[class*='next']:not([class*='disabled'])")
                        if next_btn:
                            await next_btn.click()
                            await asyncio.sleep(delay)
                        else:
                            break
                    except Exception:
                        break

        except Exception as e:
            print_warning(f"抓取出错: {e}")
        finally:
            await page.close()

        print_success(f"广西人才网共找到 {len(jobs)} 个岗位")
        return jobs

    async def _parse_card(self, card) -> Job:
        """解析单个岗位卡片（GXRC 真实DOM v2024）

        DOM 结构:
          a.position-item-left
            div.position-title
              span.position-name     → 岗位名
              span.position-area     → [城市]
            div.position-info
              span.salary            → 薪资
              ul.tag-list
                li                   → 经验(3年工龄)
                li                   → 学历(本科)
                li.emergency         → 急
              span.online-chat       → 在线直聊
          div.position-item-right
            div.company-info > a     → 公司名
            div.publish              → 发布日期
        """
        job = Job(platform=self.PLATFORM)

        # -- 主链接（URL + 岗位详情）--
        main_link = await card.query_selector("a.position-item-left")
        if not main_link:
            main_link = await card.query_selector("a[href*='jobDetail']")

        if main_link:
            href = await main_link.get_attribute("href") or ""
            job.source_url = href if href.startswith("http") else f"https://www.gxrc.com{href}"

            # 标题
            title_el = await main_link.query_selector("span.position-name")
            if title_el:
                job.title = (await title_el.inner_text()).strip()

            # 城市
            area_el = await main_link.query_selector("span.position-area")
            if area_el:
                area_text = (await area_el.inner_text()).strip().strip("[]")
                job.city = area_text

            # 薪资
            salary_el = await main_link.query_selector("span.salary")
            if salary_el:
                job.salary_text = (await salary_el.inner_text()).strip()
                self._parse_salary(job, job.salary_text)

            # 标签列表（经验/学历/急等）
            tag_items = await main_link.query_selector_all("ul.tag-list li")
            tags = []
            for li in tag_items:
                text = (await li.inner_text()).strip()
                if not text:
                    continue
                # 经验
                if re.search(r"\d+年|应届|经验不限", text) and not job.experience:
                    job.experience = text
                # 学历
                elif re.search(r"本科|硕士|博士|大专|中专|学历不限", text) and not job.education:
                    job.education = text
                else:
                    tags.append(text)
            if tags:
                job.tags = ",".join(tags)

        # -- 公司信息 --
        right = await card.query_selector("div.position-item-right")
        if right:
            # 公司名
            company_a = await right.query_selector("div.company-info a") or await right.query_selector("a")
            if company_a:
                job.company = (await company_a.inner_text()).strip()

            # 公司信息文本（企业性质/规模/行业）
            company_info = await right.query_selector("div.company-info")
            if company_info:
                info_text = (await company_info.inner_text()).strip()
                # 去掉公司名，保留其他
                if job.company:
                    info_text = info_text.replace(job.company, "").strip()
                if info_text:
                    job.benefits = info_text[:100]

            # 发布日期
            publish_el = await right.query_selector("div.publish")
            if publish_el:
                job.created_at = (await publish_el.inner_text()).strip()

        # 如果没有标题，从卡片文本取第一行
        if not job.title:
            card_text = await card.inner_text()
            lines = card_text.strip().split("\n")
            if lines:
                job.title = lines[0].strip()[:50]

        return job

    def _parse_salary(self, job: Job, text: str):
        text = text.replace("K", "000").replace("k", "000").replace("元/月", "").replace("/月", "")
        nums = re.findall(r"(\d+\.?\d*)", text)
        if len(nums) >= 2:
            try:
                lo, hi = float(nums[0]), float(nums[1])
                if "万" in text:
                    lo, hi = lo * 10000, hi * 10000
                elif lo < 100:
                    lo, hi = lo * 1000, hi * 1000
                job.salary_min, job.salary_max = int(lo), int(hi)
            except (ValueError, IndexError):
                pass
