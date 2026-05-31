"""投递记录模型"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Application:
    """投递记录"""
    id: Optional[int] = None

    job_id: int = 0
    job_title: str = ""
    company: str = ""
    platform: str = ""

    status: str = "applied"     # applied/replied/interview/offer/rejected/ignored
    applied_at: str = field(default_factory=lambda: datetime.now().isoformat())
    replied_at: Optional[str] = None
    interview_at: Optional[str] = None

    # 投递内容
    greeting: str = ""          # 打招呼语
    resume_path: str = ""       # 使用的简历文件路径
    notes: str = ""             # 备注

    # 面试信息
    interview_type: str = ""    # phone/video/onsite
    interview_notes: str = ""   # 面试记录

    @property
    def status_display(self) -> str:
        """状态中文显示"""
        mapping = {
            "applied": "🟡 已投递",
            "replied": "🟢 已回复",
            "interview": "🔵 面试中",
            "offer": "🎉 已获Offer",
            "rejected": "🔴 已拒绝",
            "ignored": "⚫ 未回复",
        }
        return mapping.get(self.status, self.status)

    @property
    def status_sort_order(self) -> int:
        """状态排序优先级"""
        order = {
            "interview": 0,
            "replied": 1,
            "applied": 2,
            "ignored": 3,
            "rejected": 4,
            "offer": 5,
        }
        return order.get(self.status, 10)
