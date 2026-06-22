"""岗位抓取器 - 真实抓取，非 LLM 编造

支持的平台:
- BOSS直聘 (boss.py) — Playwright
- 广西人才网 (gxrc.py) — Playwright + httpx fallback
- 桂聘网 (guipin.py) — httpx + BS4
- 前程无忧 (job51.py) — 待实现
- Bing 搜索 (bing.py) — 备用
"""

from .base import BaseScraper
from .boss import BossScraper
from .gxrc import GxrcScraper
from .guipin import GuiPinScaper
from .job51 import Job51Scraper
from .bing import bing_job_search
