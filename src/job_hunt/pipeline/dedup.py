"""
跨平台去重 — 同一岗位出现在多个招聘平台时合并

去重维度：
1. 公司名 + 岗位标题 相似度（编辑距离 / 关键词重叠）
2. 公司在同一城市
3. 同一 source_url（直接匹配）
"""

import re
from typing import List, Dict


def make_job_key(job) -> str:
    """生成去重键：标准化的公司+岗位+城市"""
    company = _normalize(job.company or "")
    title = _normalize(job.title or "")
    city = _normalize(job.city or "")
    return f"{company}|{title}|{city}"


def _normalize(text: str) -> str:
    """标准化文本（用于比较）"""
    # 去括号内容
    text = re.sub(r'[（(].*?[）)]', '', text)
    # 去空格
    text = re.sub(r'\s+', '', text)
    # 常见后缀
    for suffix in ['有限公司', '有限责任公司', '股份有限公司', '集团有限公司']:
        text = text.replace(suffix, '')
    return text.lower()


def dedup_jobs(jobs: List, key_func=None) -> dict:
    """对岗位列表去重

    Args:
        jobs: 岗位列表（需要有 company, title, city 属性）
        key_func: 自定义 key 函数，默认 make_job_key

    Returns:
        {"unique": [...], "duplicates": [(kept, removed), ...]}
    """
    if key_func is None:
        key_func = make_job_key

    seen: Dict[str, int] = {}  # key -> list index
    unique = []
    duplicates = []

    for i, job in enumerate(jobs):
        key = key_func(job)
        if key in seen:
            kept_idx = seen[key]
            # 保留 match_score 更高的
            kept = unique[kept_idx]
            if getattr(job, "match_score", 0) > getattr(kept, "match_score", 0):
                # 当前 job 更好，替换
                unique[kept_idx] = job
                duplicates.append((job, kept))
            else:
                duplicates.append((kept, job))
        else:
            seen[key] = len(unique)
            unique.append(job)

    return {"unique": unique, "duplicates": duplicates}


def compute_title_similarity(title1: str, title2: str) -> float:
    """计算两个岗位标题的相似度（0-1）

    使用字符级 2-gram 重叠度，对中文友好。
    """
    def bigrams(s):
        return {s[i:i+2] for i in range(len(s) - 1)}
    t1 = _normalize(title1)
    t2 = _normalize(title2)
    b1 = bigrams(t1)
    b2 = bigrams(t2)
    if not b1 or not b2:
        return 0.0
    intersection = b1 & b2
    union = b1 | b2
    return len(intersection) / len(union)


def find_cross_platform_duplicates(jobs: List) -> List[tuple]:
    """找出跨平台的重复岗位（宽松匹配）

    用标题相似度 > 0.6 + 公司名完全匹配 来判断。

    Returns:
        [(job_a, job_b, similarity), ...] 跨平台重复对
    """
    pairs = []
    for i in range(len(jobs)):
        for j in range(i + 1, len(jobs)):
            a, b = jobs[i], jobs[j]
            if getattr(a, "platform", "") == getattr(b, "platform", ""):
                continue  # 同平台不管
            company_a = _normalize(a.company or "")
            company_b = _normalize(b.company or "")
            if company_a != company_b:
                continue
            sim = compute_title_similarity(a.title or "", b.title or "")
            if sim > 0.6:
                pairs.append((a, b, sim))
    return pairs
