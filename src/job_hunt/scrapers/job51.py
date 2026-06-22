"""
前程无忧 (51job.com) 岗位抓取器
===============================
browser-act 全浏览器模式 + JS eval 提取，已验证有效（2026-06-21）。

用法:
    from job_hunt.scrapers.job51 import extract_51job
    jobs = extract_51job("python开发 南宁", max_results=15)
"""

import json
import subprocess
import shlex
import time
import re
from typing import List
from urllib.parse import quote

from ..models.job import Job


class Job51Scraper:
    """前程无忧 browser-act 抓取器"""

    platform: str = "job51"
    name: str = "前程无忧"
    base_url: str = "https://we.51job.com/pc/search"

    def __init__(self, debug: bool = False):
        self.debug = debug

    def search(self, keyword: str, city: str = "",
               max_results: int = 20, session: str = "w51") -> List[Job]:
        """搜索岗位
        注意：51job 的 jobArea 参数在 SPA 中不生效，
        城市过滤需在关键词中拼接城市名（如 "python开发 南宁"）
        """
        full_kw = f"{keyword} {city}".strip()
        url = f"{self.base_url}?keyword={quote(full_kw)}"

        js = (
            f"JSON.stringify(Array.from(document.querySelectorAll('.joblist-item'))"
            f".map(c=>({{title:(c.querySelector('.jname')?.textContent||'').trim(),"
            f"salary:(c.querySelector('.sal')?.textContent||'').trim(),"
            f"company:(c.querySelector('.cname')?.textContent||'').trim(),"
            f"url:c.querySelector('a')?.href||''}})).slice(0,{max_results}))"
        )

        return self._extract(url, js, session)

    def _extract(self, url: str, js: str, session: str) -> List[Job]:
        exe = "browser-act"
        jobs: List[Job] = []

        try:
            # Navigate
            subprocess.run(
                [exe, "--session", session, "navigate", url],
                capture_output=True, text=True, timeout=30,
            )
            time.sleep(3)

            # Extract
            r = subprocess.run(
                [exe, "--session", session, "eval", js],
                capture_output=True, text=True, timeout=15,
            )
            if r.returncode != 0:
                if self.debug:
                    print(f"  [job51] eval error: {r.stderr[:200]}")
                return jobs

            data = json.loads(r.stdout)
            for item in data:
                t = (item.get("title") or "").strip()
                if not t:
                    continue
                j = Job(
                    title=t,
                    company=(item.get("company") or "").strip(),
                    salary_text=(item.get("salary") or "").strip(),
                    platform=self.platform,
                    source_url=item.get("url", "") or "",
                )
                _parse_51salary(j, j.salary_text)
                jobs.append(j)

        except Exception as e:
            if self.debug:
                print(f"  [job51] error: {e}")

        return jobs


def _parse_51salary(job: Job, text: str) -> None:
    """解析 51job 薪资: '8千-1.5万' '1-2万·13薪'"""
    text = re.sub(r'[··•·].*', '', text).replace(" ", "")
    if not text:
        return
    parts = text.split("-")
    if len(parts) != 2:
        return
    lo, hi = parts[0], parts[1]
    job.salary_min = _num(lo)
    job.salary_max = _num(hi)


def _num(s: str) -> int:
    s = s.strip()
    if "万" in s:
        return int(float(s.replace("万", "")) * 10000)
    elif "千" in s:
        return int(float(s.replace("千", "")) * 1000)
    try:
        return int(float(s))
    except ValueError:
        return 0


def extract_51job(keyword: str, city: str = "",
                  max_results: int = 15) -> List[Job]:
    """便捷函数：直接搜索前程无忧"""
    s = Job51Scraper()
    return s.search(keyword=keyword, city=city, max_results=max_results)
