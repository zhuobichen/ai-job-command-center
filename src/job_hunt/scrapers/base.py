"""基础 HTML 抓取器 — httpx + BeautifulSoup，无需浏览器"""

import time
import json
import os
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from ..models.job import Job

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}


class BaseScraper(ABC):
    """抓取器基类"""

    platform: str = ""
    name: str = ""
    base_url: str = ""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.client = httpx.Client(
            headers=HEADERS,
            timeout=30,
            follow_redirects=True,
        )

    def close(self):
        self.client.close()

    def _get(self, url: str) -> Optional[BeautifulSoup]:
        """GET 请求并返回 BeautifulSoup"""
        try:
            r = self.client.get(url)
            r.raise_for_status()
            if self.debug:
                self._save_debug_html(url, r.text)
            return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            if self.debug:
                print(f"  [dim]请求失败 {url[:80]}: {e}[/dim]")
            return None

    def _save_debug_html(self, url: str, html: str):
        """保存调试 HTML"""
        os.makedirs("logs", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fname = f"logs/{self.platform}_{ts}.html"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"<!-- {url} -->\n")
            f.write(html[:50000])

    def _parse_job_cards(self, soup: BeautifulSoup, selectors: List[str]) -> List:
        """尝试多个选择器直到找到岗位卡片"""
        for sel in selectors:
            cards = soup.select(sel)
            if cards:
                return cards
        return []

    def _safe_text(self, el, selector: str, default: str = "") -> str:
        """安全提取文本"""
        found = el.select_one(selector)
        return found.get_text(strip=True) if found else default

    def _safe_attr(self, el, selector: str, attr: str, default: str = "") -> str:
        """安全提取属性"""
        found = el.select_one(selector)
        return found.get(attr, default) if found else default

    @abstractmethod
    def search(
        self,
        keyword: str,
        city: str = "",
        max_pages: int = 3,
        delay: float = 1.5,
    ) -> List[Job]:
        """搜索岗位"""
        ...

    @abstractmethod
    def _parse_card(self, card) -> Optional[Job]:
        """解析单个岗位卡片"""
        ...
