"""BOSS直聘岗位抓取模块 - 基于Playwright"""

import asyncio
import time
from typing import List
from datetime import datetime

from ..models.job import Job
from ..utils.display import print_status, print_info, print_success, print_warning, console


class BossScraper:
    """BOSS直聘抓取器"""

    PLATFORM = "boss"
    BASE_URL = "https://www.zhipin.com"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None

    async def _init_browser(self):
        """初始化Playwright浏览器"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print_warning("playwright 未安装，请运行: pip install playwright && playwright install chromium")
            raise

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
        # 注入反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)

    async def close(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, "_pw"):
            await self._pw.stop()

    async def search(
        self,
        keyword: str,
        city: str = "",
        max_pages: int = 5,
        delay: float = 2.0,
    ) -> List[Job]:
        """搜索岗位"""
        print_status(f"🔍 BOSS直聘 | 搜索: {keyword} | 城市: {city or '全国'}")

        await self._init_browser()
        page = await self.context.new_page()
        jobs: List[Job] = []

        try:
            # 构建搜索URL
            import urllib.parse
            query = urllib.parse.quote(f"{keyword} {city}".strip())
            search_url = f"{self.BASE_URL}/web/geek/job?query={query}"

            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(delay)

            # 检查是否被拦截
            if "verify" in page.url.lower() or "login" in page.url.lower():
                print_warning("BOSS直聘可能需要登录或验证，请手动处理后重试")
                print_info(f"当前页面: {page.url}")
                # 尝试截图保存
                try:
                    await page.screenshot(path="logs/boss_captcha.png")
                    print_info("截图已保存至 logs/boss_captcha.png")
                except Exception:
                    pass
                return jobs

            for p in range(max_pages):
                print_status(f"抓取第 {p + 1} 页...")
                await asyncio.sleep(delay)

                # 解析岗位列表
                try:
                    job_cards = await page.query_selector_all(".job-card-wrapper")
                    if not job_cards:
                        job_cards = await page.query_selector_all('[class*="job-card"]')
                except Exception:
                    job_cards = []

                if not job_cards:
                    print_warning("未找到岗位卡片，页面结构可能已变化")
                    break

                for card in job_cards:
                    try:
                        job = await self._parse_card(card)
                        if job and job.title:
                            jobs.append(job)
                    except Exception as e:
                        continue

                print_info(f"本页抓取 {len(job_cards)} 个岗位")

                # 翻页
                if p < max_pages - 1:
                    try:
                        next_btn = await page.query_selector(".options-pages a:last-child")
                        if next_btn and "disabled" not in (await next_btn.get_attribute("class") or ""):
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

        print_success(f"BOSS直聘共找到 {len(jobs)} 个岗位")
        return jobs

    async def _parse_card(self, card) -> Job:
        """解析单个岗位卡片"""
        job = Job(platform=self.PLATFORM)

        # 标题
        title_el = await card.query_selector(".job-name")
        if title_el:
            job.title = (await title_el.inner_text()).strip()

        # 公司
        company_el = await card.query_selector(".company-name")
        if company_el:
            company_link = await company_el.query_selector("a")
            if company_link:
                job.company = (await company_link.inner_text()).strip()
            else:
                job.company = (await company_el.inner_text()).strip()

        # 城市
        city_el = await card.query_selector(".job-area")
        if city_el:
            job.city = (await city_el.inner_text()).strip()

        # 薪资
        salary_el = await card.query_selector(".salary")
        if salary_el:
            salary_text = (await salary_el.inner_text()).strip()
            job.salary_text = salary_text
            # 解析薪资范围 如 "10-15K"
            try:
                parts = salary_text.replace("K", "000").replace("k", "000").split("-")
                if len(parts) == 2:
                    job.salary_min = int(float(parts[0].strip()) * 1000)
                    job.salary_max = int(float(parts[1].strip()) * 1000)
            except Exception:
                pass

        # 经验/学历
        tag_els = await card.query_selector_all(".tag-list li")
        tags = []
        for tag_el in tag_els:
            tag_text = (await tag_el.inner_text()).strip()
            tags.append(tag_text)
            if "年" in tag_text or "经验" in tag_text:
                job.experience = tag_text
            elif any(d in tag_text for d in ["本科", "硕士", "博士", "大专", "学历"]):
                job.education = tag_text
        job.tags = ",".join(tags)

        # 岗位描述摘要
        desc_el = await card.query_selector(".job-info")
        if desc_el:
            job.description = (await desc_el.inner_text()).strip()[:500]

        # 福利
        benefits_el = await card.query_selector(".info-desc")
        if benefits_el:
            job.benefits = (await benefits_el.inner_text()).strip()[:200]

        # 链接
        link_el = await card.query_selector("a")
        if link_el:
            href = await link_el.get_attribute("href")
            if href:
                job.source_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href

        return job


async def scan_boss(
    keyword: str,
    city: str = "",
    max_pages: int = 5,
    headless: bool = True,
) -> List[Job]:
    """便捷入口：扫描BOSS直聘"""
    scraper = BossScraper(headless=headless)
    try:
        jobs = await scraper.search(keyword=keyword, city=city, max_pages=max_pages)
        return jobs
    finally:
        await scraper.close()
