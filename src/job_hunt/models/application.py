"""投递记录模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Application:
    """投递记录"""
    id: Optional[int] = None

    job_id: int = 0
    job_title: str = ""
    company: str = ""
    platform: str = ""

    # 状态对齐 career-ops 规范: evaluated/applied/responded/interview/offer/rejected/discarded/skip/ignored
    status: str = "applied"
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
        """状态中文显示（对齐 career-ops 规范）"""
        mapping = {
            "evaluated": "[?] 已评估",
            "applied": "[*] 已投递",
            "responded": "[->] 已回复",
            "interview": "[!!] 面试中",
            "offer": "[OK] 已获Offer",
            "rejected": "[X] 已拒绝",
            "discarded": "[-] 已放弃",
            "skip": "[SKIP] 跳过",
            "ignored": "[.] 未回复",
        }
        return mapping.get(self.status, self.status)

    @property
    def status_sort_order(self) -> int:
        """状态排序优先级（对齐 career-ops 规范）"""
        order = {
            "interview": 0,
            "responded": 1,
            "applied": 2,
            "evaluated": 3,
            "ignored": 4,
            "rejected": 5,
            "offer": 6,
            "discarded": 7,
            "skip": 8,
        }
        return order.get(self.status, 10)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "job_title": self.job_title,
            "company": self.company,
            "platform": self.platform,
            "status": self.status,
            "applied_at": self.applied_at,
            "replied_at": self.replied_at,
            "interview_at": self.interview_at,
            "greeting": self.greeting,
            "resume_path": self.resume_path,
            "notes": self.notes,
            "interview_type": self.interview_type,
            "interview_notes": self.interview_notes,
        }
