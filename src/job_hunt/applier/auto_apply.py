"""自动投递模块 - Playwright自动化投递"""

import asyncio
from typing import Optional

from ..models.job import Job
from ..utils.display import print_info, print_success, print_warning


class AutoApplier:
    """自动投递引擎"""

    def __init__(self):
        self.browser = None
        self.context = None

    async def _init_browser(self):
        """初始化浏览器"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError("需要安装 playwright")

        self._pw = await async_playwright().start()
        # 使用本地Chrome，保留登录态
        self.browser = await self._pw.chromium.launch(
            headless=False,  # 投递需要可见浏览器
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

    async def apply_boss(self, job: Job, resume_path: str, greeting: str) -> bool:
        """
        在BOSS直聘上投递岗位
        注意：需要用户已经在浏览器中登录BOSS直聘
        """
        print_info(f"🤖 正在打开BOSS直聘投递: {job.title} - {job.company}")

        await self._init_browser()
        page = await self.context.new_page()

        try:
            # 打开岗位详情页
            if job.source_url:
                await page.goto(job.source_url, wait_until="domcontentloaded", timeout=30000)
            else:
                print_warning("缺少岗位URL，无法投递")
                return False

            await asyncio.sleep(2)

            # 检查登录状态
            if "login" in page.url.lower():
                print_warning("🔐 请在浏览器中登录BOSS直聘，然后按回车继续...")
                input("按回车继续...")
                await page.goto(job.source_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)

            # 尝试找到"立即沟通"按钮
            try:
                chat_btn = await page.query_selector("text=立即沟通")
                if not chat_btn:
                    chat_btn = await page.query_selector("text=立即沟通")
                if not chat_btn:
                    chat_btn = await page.query_selector('[class*="btn-chat"]')
            except Exception:
                chat_btn = None

            if chat_btn:
                await chat_btn.click()
                print_info("✅ 点击了沟通按钮")
                await asyncio.sleep(2)

                # 输入打招呼语
                try:
                    input_area = await page.query_selector("textarea, [contenteditable]")
                    if input_area:
                        await input_area.fill(greeting)
                        await asyncio.sleep(0.5)

                        # 发送
                        send_btn = await page.query_selector("[class*='send']")
                        if send_btn:
                            await send_btn.click()
                            print_success(f"已发送打招呼语: {greeting}")
                        else:
                            # 尝试回车发送
                            await page.keyboard.press("Enter")
                            print_success(f"已发送打招呼语")
                except Exception as e:
                    print_warning(f"输入打招呼语失败: {e}")

                # 如果有简历按钮，尝试发送简历
                try:
                    resume_btn = await page.query_selector("text=发简历")
                    if not resume_btn:
                        resume_btn = await page.query_selector("[class*='resume']")
                    if resume_btn:
                        await resume_btn.click()
                        print_success("已发送简历")
                except Exception:
                    pass

                return True
            else:
                print_warning("未找到沟通按钮，可能需要手动操作")
                print_info(f"请手动在浏览器中完成投递: {job.source_url}")
                return False

        except Exception as e:
            print_warning(f"投递出错: {e}")
            return False
        finally:
            print_info("浏览器窗口保持打开，请确认投递完成后关闭")
