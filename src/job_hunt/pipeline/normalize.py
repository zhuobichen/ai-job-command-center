"""
投递状态标准化 — 对齐 career-ops 规范状态机

规范状态流转:
    Evaluated -> Applied -> Responded -> Interview -> Offer
                     ↘ Rejected / Discarded / SKIP / Ignored
"""

CANONICAL_STATES = {
    "evaluated": {
        "label": "Evaluated",
        "aliases": ["已评估", "évaluée"],
        "group": "evaluated",
        "description": "岗位已评估，待决定是否投递",
    },
    "applied": {
        "label": "Applied",
        "aliases": ["已投递", "投递", "aplicado", "sent", "enviada"],
        "group": "applied",
        "description": "已提交投递申请",
    },
    "responded": {
        "label": "Responded",
        "aliases": ["已回复", "回复", "respondido"],
        "group": "responded",
        "description": "HR 已回复",
    },
    "interview": {
        "label": "Interview",
        "aliases": ["面试中", "面试", "entrevista"],
        "group": "interview",
        "description": "面试流程中",
    },
    "offer": {
        "label": "Offer",
        "aliases": ["已获Offer", "offer", "oferta"],
        "group": "offer",
        "description": "已收到 Offer",
    },
    "rejected": {
        "label": "Rejected",
        "aliases": ["已拒绝", "拒绝", "被拒", "rechazado"],
        "group": "rejected",
        "description": "被公司拒绝",
    },
    "discarded": {
        "label": "Discarded",
        "aliases": ["已放弃", "放弃", "取消", "descartado", "closed"],
        "group": "discarded",
        "description": "候选人放弃或岗位已关闭",
    },
    "skip": {
        "label": "SKIP",
        "aliases": ["跳过", "不适合", "skip", "no_aplicar"],
        "group": "skip",
        "description": "不匹配，不投递",
    },
    "ignored": {
        "label": "Ignored",
        "aliases": ["未回复", "无回应", "ignored", "ghosted"],
        "group": "ignored",
        "description": "投递后 HR 未回复",
    },
}


def normalize_status(raw: str) -> str:
    """将任意状态文本标准化为规范状态 ID

    Args:
        raw: 原始状态文本（中文/英文/西班牙语等）

    Returns:
        规范状态 ID（如 "applied"），未匹配返回 "applied" 作为默认值
    """
    if not raw:
        return "applied"

    raw_lower = raw.strip().lower()

    # 精确匹配 ID
    if raw_lower in CANONICAL_STATES:
        return raw_lower

    # 别名匹配
    for state_id, info in CANONICAL_STATES.items():
        for alias in info["aliases"]:
            if alias.lower() in raw_lower:
                return state_id
        if info["label"].lower() in raw_lower:
            return state_id

    # 未匹配的默认: 保守选择 "evaluated"（已评估但状态不明）而非 "applied"（未投递误标为已投递）
    return "evaluated"


def get_state_label(state_id: str) -> str:
    """获取状态的中文标签"""
    info = CANONICAL_STATES.get(state_id)
    return info["label"] if info else state_id


def get_state_group(state_id: str) -> str:
    """获取状态所属分组"""
    info = CANONICAL_STATES.get(state_id)
    return info.get("group", "") if info else ""


def get_status_sort_order(state_id: str) -> int:
    """获取状态的排序优先级（升序=优先显示）"""
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
    return order.get(state_id, 10)


def validate_pipeline(db) -> dict:
    """管道健康检查

    Returns:
        {
            "total_jobs": N,
            "total_applications": N,
            "orphan_applications": [...],  # application 无对应 job
            "stale_jobs": [...],            # 超过90天未更新的岗位
            "dup_count": N,                 # 疑似重复数
        }
    """
    from datetime import datetime, timedelta

    result = {
        "total_jobs": 0,
        "total_applications": 0,
        "orphan_applications": [],
        "stale_jobs": [],
        "dup_count": 0,
    }

    try:
        jobs = db.get_jobs(limit=10000, active_only=False)
        apps = db.get_applications(limit=10000)

        result["total_jobs"] = len(jobs)
        result["total_applications"] = len(apps)

        # 检查孤儿投递（application 指向不存在的 job）
        job_ids = {j.id for j in jobs}
        for app in apps:
            if app.job_id not in job_ids and app.job_id > 0:
                result["orphan_applications"].append({
                    "app_id": app.id,
                    "job_id": app.job_id,
                    "job_title": app.job_title,
                })

        # 检查过期岗位
        cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        for job in jobs:
            scraped = getattr(job, "scraped_at", "")
            if scraped and scraped < cutoff:
                result["stale_jobs"].append({
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "scraped_at": scraped,
                })

    except Exception as e:
        result["error"] = str(e)

    return result
