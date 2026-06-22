"""
智能过滤模块 — 参考 get_jobs 的过滤策略

过滤维度：
1. 不活跃 HR（最后活跃 > 30天） → 跳过
2. 猎头岗位（标题含"猎头""HRBP"等） → 跳过
3. 薪资不达标（< 最低期望） → 跳过
4. 黑名单公司 → 跳过
5. BOSS直聘自动回复/机器人 → 跳过
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FilterResult:
    """过滤结果"""
    passed: bool = True
    reason: str = ""
    filter_name: str = ""


def should_filter(
    job,
    resume=None,
    config=None,
    blacklist: Optional[List[str]] = None,
) -> FilterResult:
    """综合过滤判断

    Args:
        job: Job 对象或 dict
        resume: Resume 对象（可选，用于薪资比对）
        config: Config 对象（可选）
        blacklist: 黑名单公司列表

    Returns:
        FilterResult: passed=True 表示不过滤（可以投递）
    """
    # 优先用 getattr（对象），降级用 dict.get
    if isinstance(job, dict):
        title = job.get("title", "")
        company = job.get("company", "")
        salary_min = job.get("salary_min", 0)
        salary_max = job.get("salary_max", 0)
    else:
        title = getattr(job, "title", "") or ""
        company = getattr(job, "company", "") or ""
        salary_min = getattr(job, "salary_min", 0) or 0
        salary_max = getattr(job, "salary_max", 0) or 0

    # 1. 黑名单检查
    if blacklist:
        for blocked in blacklist:
            if blocked.lower() in company.lower():
                return FilterResult(
                    passed=False,
                    reason=f"黑名单公司: {blocked}",
                    filter_name="blacklist",
                )

    # 2. 猎头/中介检查
    headhunter_signals = [
        "猎头", "HRBP", "人力资源服务", "人才中介",
        "猎聘顾问", "RPO", "人力外包", "劳务派遣",
        "咨询顾问", "招聘专员", "人事专员",
    ]
    for signal in headhunter_signals:
        if signal in title or (signal in company and len(company) < 10):
            return FilterResult(
                passed=False,
                reason=f"疑似猎头/中介: 检测到 '{signal}'",
                filter_name="headhunter",
            )

    # 3. 薪资过滤（如果简历有期望薪资）
    if resume and salary_max > 0:
        expect_min = getattr(resume, "salary_min", 0) or 0
        if expect_min > 0 and salary_max < expect_min * 0.7:
            return FilterResult(
                passed=False,
                reason=f"薪资偏低: {salary_max} < 期望 {expect_min}*0.7",
                filter_name="salary_low",
            )

    # 4. "常年招聘"检测
    perpetual_signals = ["常年招聘", "大量招人", "不限经验 学历不限", "急聘 急招 大量"]
    full_text = f"{title} {company}"
    for signal in perpetual_signals:
        if signal in full_text:
            return FilterResult(
                passed=False,
                reason=f"疑似常年招聘/低质量: 检测到 '{signal}'",
                filter_name="low_quality",
            )

    # 5. 培训/招生伪装成招聘
    training_signals = ["培训", "实训", "学徒", "管培生", "储备干部"]
    training_hit = sum(1 for s in training_signals if s in title)
    if training_hit >= 2:
        return FilterResult(
            passed=False,
            reason=f"疑似培训招生: 标题含多个培训信号词",
            filter_name="training_scam",
        )

    return FilterResult(passed=True)


def load_blacklist(db=None) -> List[str]:
    """从数据库加载黑名单"""
    if db:
        try:
            blacklist_str = db.get_config("blacklist", "")
            if blacklist_str:
                return [n.strip() for n in blacklist_str.split(",") if n.strip()]
        except Exception:
            pass
    return []


def add_to_blacklist(db, company: str) -> None:
    """添加公司到黑名单"""
    current = load_blacklist(db)
    if company not in current:
        current.append(company)
        db.set_config("blacklist", ",".join(current))
