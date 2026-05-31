"""简历数据模型"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Resume:
    """结构化简历"""
    id: Optional[int] = None
    name: str = ""
    phone: str = ""
    email: str = ""
    wechat: Optional[str] = None

    # 求职意向
    desired_city: str = ""
    desired_position: str = ""
    desired_industry: str = ""
    salary_min: int = 0
    salary_max: int = 0

    # 教育背景
    education_level: str = ""          # 本科/硕士/博士
    university: str = ""
    major: str = ""
    graduation_year: int = 0

    # 项目经验
    projects: str = ""                 # JSON字符串存储项目列表
    skills: str = ""                   # 逗号分隔的技能列表
    work_years: int = 0

    # 原始简历
    raw_text: str = ""                 # 原始简历文本
    raw_file_path: str = ""            # 原始简历文件路径

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "phone": self.phone,
            "email": self.email,
            "wechat": self.wechat,
            "desired_city": self.desired_city,
            "desired_position": self.desired_position,
            "desired_industry": self.desired_industry,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "education_level": self.education_level,
            "university": self.university,
            "major": self.major,
            "graduation_year": self.graduation_year,
            "projects": self.projects,
            "skills": self.skills,
            "work_years": self.work_years,
            "raw_text": self.raw_text,
            "raw_file_path": self.raw_file_path,
        }

    def summary(self) -> str:
        """简历摘要"""
        parts = []
        if self.name:
            parts.append(self.name)
        if self.education_level and self.major:
            parts.append(f"{self.education_level}-{self.major}")
        if self.desired_position:
            parts.append(f"意向: {self.desired_position}")
        if self.desired_city:
            parts.append(f"城市: {self.desired_city}")
        if self.salary_min and self.salary_max:
            parts.append(f"薪资: {self.salary_min / 1000:.0f}-{self.salary_max / 1000:.0f}K")
        return " | ".join(parts)
