"""岗位数据模型"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Job:
    """招聘岗位"""
    id: Optional[int] = None

    # 基本信息
    title: str = ""
    company: str = ""
    city: str = ""
    district: str = ""
    salary_min: int = 0         # 单位：元
    salary_max: int = 0
    salary_text: str = ""       # 原始薪资文本

    # 岗位详情
    description: str = ""       # 岗位描述（完整JD）
    requirements: str = ""      # 任职要求
    tags: str = ""              # 技术标签，逗号分隔
    experience: str = ""        # 经验要求
    education: str = ""         # 学历要求
    benefits: str = ""          # 福利待遇

    # 来源信息
    platform: str = ""          # boss/zhilian/liepin/job51/guipin/gxrc
    source_url: str = ""
    source_id: str = ""         # 平台原始ID

    # AI评估结果
    match_score: float = 0.0    # 匹配度 0-100
    match_detail: str = ""      # 匹配详情 JSON
    eval_score: str = ""        # A-F评分
    eval_detail: str = ""       # 评估详情 JSON
    recommend_reason: str = ""  # 推荐理由

    # 状态
    is_active: bool = True
    is_deleted: bool = False

    # 元数据
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "city": self.city,
            "district": self.district,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_text": self.salary_text,
            "description": self.description,
            "requirements": self.requirements,
            "tags": self.tags,
            "experience": self.experience,
            "education": self.education,
            "benefits": self.benefits,
            "platform": self.platform,
            "source_url": self.source_url,
            "source_id": self.source_id,
            "match_score": self.match_score,
            "match_detail": self.match_detail,
            "eval_score": self.eval_score,
            "eval_detail": self.eval_detail,
            "recommend_reason": self.recommend_reason,
            "is_active": self.is_active,
            "scraped_at": self.scraped_at,
        }

    @property
    def salary_range_display(self) -> str:
        if self.salary_text:
            return self.salary_text
        if self.salary_min and self.salary_max:
            return f"{self.salary_min / 1000:.0f}-{self.salary_max / 1000:.0f}K"
        return "面议"

    @property
    def platform_display(self) -> str:
        """平台中文名"""
        mapping = {
            "boss": "BOSS直聘",
            "zhilian": "智联招聘",
            "liepin": "猎聘",
            "job51": "前程无忧",
            "guipin": "桂聘网",
            "gxrc": "广西人才网",
        }
        return mapping.get(self.platform, self.platform)
