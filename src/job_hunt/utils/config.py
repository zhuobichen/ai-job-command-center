"""配置管理模块 - 读取/写入 TOML 配置文件"""

import os
from typing import Optional
from pathlib import Path

try:
    import tomllib as _toml_reader
except ImportError:
    import tomli as _toml_reader

try:
    import tomli_w as _toml_writer
except ImportError:
    _toml_writer = None


DEFAULT_CONFIG = """\
# AI智慧求职系统 - 用户配置

[user]
name = ""
phone = ""
email = ""
wechat = ""

[preferences]
# 优先城市（逗号分隔，按优先级排序）
# 广西: 南宁 > 柳州 > 桂林 > 玉林/北海/钦州/梧州/防城港/百色/河池/贵港/贺州/来宾/崇左
# 广东: 广州 > 深圳 > 东莞 > 佛山 > 珠海 > 中山 > 惠州
cities = "南宁,广州"
# 意向岗位
position = ""
# 意向行业
industry = ""
# 最低月薪（元）
salary_min = 6000
# 最高月薪（元）
salary_max = 12000
# 学历
education = "硕士"

[ai]
# LLM API配置（兼容 OpenAI/Claude/通义千问/文心一言/DeepSeek）
provider = "deepseek"
model = "deepseek-chat"
# API key（留空则自动从环境变量 DEEPSEEK_API_KEY 读取，与 weflow-cli 一致）
api_key = ""
# API Base URL（留空默认 https://api.deepseek.com）
api_base = ""

[platforms]
# 需要抓取的招聘平台
boss = true
zhilian = false
liepin = false
job51 = false
guipin = true
gxrc = true

[scanner]
# 扫描相关设置
max_pages = 5
scan_interval_hours = 24
# 搜索关键词（逗号分隔）
# 广西重点方向: Python开发 / 数据分析 / AI信息化 / 环境科技 / 政府事业
keywords = "Python 开发,数据分析,人工智能,信息化,环保工程师,环境监测,软件开发,Python 工程师"

[output]
# 简历输出目录
resume_dir = "output"

# ======================
# 高级配置（可选）
# ======================

[advanced]
# browser-act 集成（需要安装: uv tool install browser-act-cli --python 3.12）
browser_act_enabled = false
# 自动去重（跨平台）
auto_dedup = true
# 伦理约束：低于此分数不允许自动投递
min_apply_score = 4.0
"""


class Config:
    """配置管理器"""

    def __init__(self, config_path: str = "config.toml"):
        self.config_path = config_path
        self._data: dict = {}
        self._load()

    def _load(self):
        """加载配置文件，不存在则创建默认配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "rb") as f:
                self._data = _toml_reader.load(f)
        else:
            self._data = _toml_reader.loads(DEFAULT_CONFIG)
            self.save()

    def save(self):
        """保存配置到文件"""
        if _toml_writer is None:
            import json as _json
            with open(self.config_path, "w", encoding="utf-8") as f:
                _json.dump(self._data, f, ensure_ascii=False, indent=2)
            return
        with open(self.config_path, "wb") as f:
            _toml_writer.dump(self._data, f)

    def get(self, section: str, key: str, default=None):
        """获取配置项"""
        return self._data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value):
        """设置配置项"""
        if section not in self._data:
            self._data[section] = {}
        self._data[section][key] = value
        self.save()

    def get_all(self, section: str) -> dict:
        """获取整个配置段"""
        return self._data.get(section, {})

    @property
    def data(self) -> dict:
        return self._data

    @property
    def user(self) -> dict:
        return self._data.get("user", {})

    @property
    def preferences(self) -> dict:
        return self._data.get("preferences", {})

    @property
    def ai(self) -> dict:
        return self._data.get("ai", {})

    @property
    def platforms(self) -> dict:
        return self._data.get("platforms", {})

    @property
    def keywords(self) -> str:
        return self._data.get("scanner", {}).get("keywords", "")

    @property
    def cities(self) -> str:
        return self._data.get("preferences", {}).get("cities", "")

    @property
    def is_configured(self) -> bool:
        """检查是否已完成基本配置（配置文件或环境变量有 API key 即可）"""
        ai = self.ai
        return bool(ai.get("api_key", "")) or bool(os.environ.get("DEEPSEEK_API_KEY", ""))

    def get_api_key(self) -> str:
        """获取 API key（优先级：配置文件 > 环境变量 DEEPSEEK_API_KEY）"""
        ai = self.ai
        return ai.get("api_key", "") or os.environ.get("DEEPSEEK_API_KEY", "")
