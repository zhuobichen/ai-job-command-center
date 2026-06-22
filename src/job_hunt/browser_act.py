"""
browser-act 集成模块
====================
将 browser-act CLI 的能力嵌入 ai-job-hunt 工作流：
- stealth-extract: 无状态 JS 渲染提取（替代 httpx 处理 SPA 页面）
- full browser: 登录态操作（BOSS直聘沟通、投递）

使用方式：
    from job_hunt.browser_act import BrowserAct

    ba = BrowserAct()
    # 轻量提取
    md = ba.stealth_extract("https://s.gxrc.com/s?q=Python")
    # 完整浏览器
    ba.open("boss", "https://www.zhipin.com")
    ba.navigate("boss", "https://www.zhipin.com/web/geek/job?query=Python")
    content = ba.get_markdown("boss")
    ba.close("boss")
"""

import shlex
import subprocess
import os
import shutil
from typing import Optional, List


def _find_browser_act() -> Optional[str]:
    """查找 browser-act 可执行文件路径"""
    # 优先用 uv tool 安装的
    path = shutil.which("browser-act")
    if path:
        return path
    # 尝试 uvx 方式
    path = shutil.which("uvx")
    if path:
        return "uvx browser-act-cli"
    return None


def _build_cmd(args: List[str], timeout: int = 60) -> subprocess.CompletedProcess:
    """安全执行 browser-act 命令（使用列表参数避免 shell 注入）

    Args:
        args: 命令参数列表，如 ["stealth-extract", "https://...", "--content-type", "markdown"]
        timeout: 超时秒数

    Returns:
        subprocess.CompletedProcess
    """
    exe = _find_browser_act()
    if not exe:
        raise RuntimeError("browser-act not found")

    # 拆分可执行文件路径（如 "uvx browser-act-cli"）
    exe_parts = shlex.split(exe)
    full_cmd = exe_parts + args

    return subprocess.run(
        full_cmd,
        shell=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class BrowserAct:
    """browser-act CLI 的 Python 封装

    设计原则：
    - stealth-extract 用于只读抓取（无需登录的搜索页）
    - full browser 用于需要登录态的操作（BOSS沟通、投递）
    - 所有操作返回 JSON 或 Markdown 文本，便于下游解析
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._check_installed()

    # ------------------------------------------------------------------
    def _check_installed(self) -> None:
        """检查 browser-act 是否可用"""
        path = _find_browser_act()
        if not path:
            raise RuntimeError(
                "browser-act 未安装。请运行: uv tool install browser-act-cli --python 3.12\n"
                "详见: https://github.com/your-tools/browser-act"
            )

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(f"  [browser-act] {msg}")

    # ==================================================================
    # 轻量提取 — stealth-extract（替代 WebFetch / httpx）
    # ==================================================================

    # ------------------------------------------------------------------
    @staticmethod
    def _check_result(result: subprocess.CompletedProcess, op: str) -> None:
        """检查命令结果，失败抛异常"""
        if result.returncode != 0:
            raise RuntimeError(f"{op} failed (rc={result.returncode}): {result.stderr[:200]}")

    def stealth_extract(self, url: str, content_type: str = "markdown") -> str:
        """无状态提取页面内容（JS 渲染后）"""
        self._log(f"stealth-extract: {url}")
        result = _build_cmd(
            ["stealth-extract", url, "--content-type", content_type],
            timeout=30,
        )
        self._check_result(result, "stealth-extract")
        return result.stdout

    def search_and_extract(
        self,
        search_url: str,
        item_selector: str = "",
    ) -> dict:
        """搜索并提取结构化结果"""
        html = self.stealth_extract(search_url, content_type="html")
        return {"html": html, "items": []}

    # ==================================================================
    # 完整浏览器操作 — 用于登录态流程
    # ==================================================================

    def open(
        self,
        session: str,
        browser_id: str,
        url: str = "",
        headed: bool = False,
    ) -> None:
        """打开浏览器并创建 session"""
        self._log(f"open session={session} browser={browser_id}")
        args = ["--session", session, "browser", "open", browser_id]
        if url:
            args.append(url)
        if headed:
            args.append("--headed")
        result = _build_cmd(args, timeout=15)
        self._check_result(result, "browser open")

    def navigate(self, session: str, url: str) -> None:
        """导航到新 URL"""
        self._log(f"navigate session={session} -> {url}")
        result = _build_cmd(
            ["--session", session, "navigate", url], timeout=30
        )
        self._check_result(result, "navigate")

    def state(self, session: str) -> str:
        """获取页面可交互元素索引"""
        result = _build_cmd(["--session", session, "state"], timeout=10)
        self._check_result(result, "state")
        return result.stdout

    def get_markdown(self, session: str) -> str:
        """获取页面 Markdown 内容"""
        result = _build_cmd(["--session", session, "get", "markdown"], timeout=15)
        self._check_result(result, "get markdown")
        return result.stdout

    def get_html(self, session: str) -> str:
        """获取页面 HTML"""
        result = _build_cmd(["--session", session, "get", "html"], timeout=15)
        self._check_result(result, "get html")
        return result.stdout

    def click(self, session: str, index: int) -> None:
        """点击元素"""
        result = _build_cmd(["--session", session, "click", str(index)], timeout=10)
        self._check_result(result, f"click {index}")

    def input_text(self, session: str, index: int, text: str) -> None:
        """在输入框中输入文本"""
        result = _build_cmd(
            ["--session", session, "input", str(index), text], timeout=10
        )
        self._check_result(result, f"input {index}")

    def wait_stable(self, session: str, timeout: int = 30000) -> None:
        """等待页面稳定"""
        result = _build_cmd(
            ["--session", session, "wait", "stable", "--timeout", str(timeout)],
            timeout=35,
        )
        self._check_result(result, "wait stable")

    def screenshot(self, session: str, path: str = "") -> str:
        """截图"""
        args = ["--session", session, "screenshot"]
        if path:
            args.append(path)
        result = _build_cmd(args, timeout=15)
        self._check_result(result, "screenshot")
        return path

    def close(self, session: str) -> None:
        """关闭 session"""
        self._log(f"close session={session}")
        result = _build_cmd(["session", "close", session], timeout=10)
        self._check_result(result, "session close")

    @staticmethod
    def list_browsers() -> str:
        """列出可用浏览器"""
        try:
            result = _build_cmd(["browser", "list"], timeout=10)
            return result.stdout if result.returncode == 0 else ""
        except (RuntimeError, subprocess.TimeoutExpired):
            return ""

    @staticmethod
    def list_sessions() -> str:
        """列出活跃 session"""
        try:
            result = _build_cmd(["session", "list"], timeout=10)
            return result.stdout if result.returncode == 0 else ""
        except (RuntimeError, subprocess.TimeoutExpired):
            return ""

    # ==================================================================
    # 高级：求职场景专用方法
    # ==================================================================

    def extract_job_list(
        self,
        url: str,
        platform: str = "",
    ) -> str:
        """提取岗位列表页 Markdown

        使用 stealth-extract 获取 JS 渲染后的岗位列表，
        比 httpx + BS4 更可靠（处理 SPA 页面）。
        """
        self._log(f"extract job list from {platform}: {url}")
        md = self.stealth_extract(url, content_type="markdown")
        # 截断过长内容（岗位列表通常前 30000 字就够了）
        return md[:30000]

    def extract_job_detail(self, url: str) -> str:
        """提取岗位详情页内容"""
        self._log(f"extract job detail: {url}")
        return self.stealth_extract(url, content_type="markdown")

    def try_login(
        self,
        session: str,
        browser_id: str,
        login_url: str,
        headed: bool = True,
    ) -> bool:
        """引导用户在浏览器中登录

        Args:
            session: 会话名
            browser_id: 浏览器 ID
            login_url: 登录页面 URL
            headed: 必须 visible（用户要手动扫码/输入）

        Returns:
            True 如果登录成功（用户确认）
        """
        self._log(f"try login at {login_url}")
        self.open(session, browser_id, login_url, headed=headed)
        print(f"\n🔐 请在浏览器中完成登录（{login_url}）")
        print("   登录完成后，在此处按回车继续...")
        input()
        print("   ✅ 登录确认")
        return True


# ==================================================================
# 便捷函数
# ==================================================================

def is_available() -> bool:
    """检查 browser-act 是否可用"""
    return _find_browser_act() is not None


def get_install_instructions() -> str:
    """获取安装说明"""
    return (
        "browser-act 未安装。安装方法:\n"
        "  uv tool install browser-act-cli --python 3.12\n"
        "  # 或\n"
        "  pip install browser-act-cli\n"
        "\n"
        "安装后运行 browser-act --help 验证。"
    )
