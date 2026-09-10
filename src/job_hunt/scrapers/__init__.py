"""岗位发现 - 真实抓取 + 多源搜索引擎，非 LLM 编造

支持的平台:
- BOSS直聘 (boss.py) — Playwright
- 广西人才网 (gxrc.py) — Playwright + httpx fallback
- 桂聘网 (guipin.py) — httpx + BS4
- 前程无忧 (job51.py) — httpx
- Bing 搜索 (bing.py) — 备用
"""

from .base import BaseScraper
from .bing import bing_job_search
from .boss import BossScraper
from .engine import import_from_agent, multi_search, search_web, verify_search
from .guipin import GuiPinScaper
from .gxrc import GxrcScraper
from .job51 import Job51Scraper
from .platforms import (
    DIRECT_GOV_SITES,
    GUANGXI_SITES,
    SearchSite,
    generate_direct_queries,
    generate_search_queries,
    get_verify_queries,
)
