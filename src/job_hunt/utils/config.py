"""配置管理模块 - 读取/写入 TOML 配置文件"""

import os
import tomli
import tomli_w
from typing import Optional
from pathlib import Path


DEFAULT_CONFIG = """\
# AI智慧求职系统 - 用户配置

[user]
name = ""
phone = ""
email = ""
wechat = ""

[preferences]
# 优先城市（逗号分隔）
cities = "广西"
# 意向岗位
position = ""
# 意向行业
industry = ""
# 最低月薪（元）
salary_min = 8000
# 最高月薪（元）
salary_max = 15000
# 学历
education = "硕士"

[ai]
# LLM API配置（兼容 OpenAI/Claude/通义千问/文心一言）
provider = "openai"
model = "gpt-4o-mini"
api_key = ""
api_base = ""

[platforms]
# 需要抓取的招聘平台
boss = true
zhilian = false
liepin = false
job51 = false
guipin = false
gxrc = false

[scanner]
# 扫描相关设置
max_pages = 5
scan_interval_hours = 24
# 搜索关键词（逗号分隔）
keywords = ""

[output]
# 简历输出目录
resume_dir = "output"
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
                self._data = tomli.load(f)
        else:
            self._data = tomli.loads(DEFAULT_CONFIG)
            self.save()

    def save(self):
        """保存配置到文件"""
        with open(self.config_path, "wb") as f:
            tomli_w.dump(self._data, f)

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
        """检查是否已完成基本配置"""
        ai = self.ai
        has_ai = bool(ai.get("api_key", ""))
        return has_ai
