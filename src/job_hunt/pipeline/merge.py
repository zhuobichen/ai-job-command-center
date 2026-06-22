"""
合并追踪记录 — 将增量评估结果合并到主追踪表

用法：
    from job_hunt.pipeline.merge import write_tsv_addition, merge_tracker

    # 每次评估后写入增量
    write_tsv_addition("output/tracker_additions/", num, company, role, score, ...)

    # 定期合并
    merge_tracker(db, additions_dir)
"""

import os
import json
import csv
from datetime import datetime
from typing import Optional

from ..db.database import Database
from ..models.job import Job


def write_tsv_addition(
    additions_dir: str,
    num: int,
    company: str,
    role: str,
    score: float,
    status: str = "Evaluated",
    pdf_path: str = "",
    report_path: str = "",
    notes: str = "",
) -> str:
    """写入一条 TSV 增量记录（兼容 career-ops 格式）

    列顺序: num, date, company, role, status, score, pdf_emoji, report_link, notes
    """
    os.makedirs(additions_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_company = (company or "Unknown").replace(" ", "-").replace("（", "").replace("）", "").replace("(", "").replace(")", "")
    slug = safe_company[:20]
    filename = f"{num:03d}-{slug}.tsv"
    filepath = os.path.join(additions_dir, filename)

    pdf_emoji = "done" if pdf_path else "not_done"
    report_link = f"[{num:03d}]({report_path})" if report_path else ""
    score_str = f"{score:.1f}/5"

    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow([
            str(num), date_str, company, role, status, score_str,
            pdf_emoji, report_link, notes,
        ])

    return filepath


def merge_tracker(
    db: Database,
    additions_dir: str,
    dry_run: bool = False,
) -> dict:
    """合并增量到数据库

    读取 additions_dir 下所有 .tsv 文件，合并到 jobs 表和 applications 表。
    自动跳过已存在的记录（根据 company+role 去重）。

    Returns:
        {"merged": N, "skipped": N, "errors": [...]}
    """
    result = {"merged": 0, "skipped": 0, "errors": []}

    if not os.path.isdir(additions_dir):
        return result

    for fname in sorted(os.listdir(additions_dir)):
        if not fname.endswith(".tsv"):
            continue

        fpath = os.path.join(additions_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter="\t")
                for row in reader:
                    if len(row) < 6:
                        continue
                    num, date, company, role, status, score_str = row[:6]
                    notes = row[8] if len(row) > 8 else ""

                    # 检查是否已存在（精确匹配 公司名+岗位标题）
                    all_jobs = db.get_jobs(limit=10000, active_only=False)
                    dup = [
                        j for j in all_jobs
                        if (company.lower() in (j.company or "").lower()
                            or (j.company or "").lower() in company.lower())
                        and role.lower() in (j.title or "").lower()
                    ]

                    if dup:
                        result["skipped"] += 1
                        continue

                    if not dry_run:
                        try:
                            score_val = float(score_str.replace("/5", "").strip())
                        except (ValueError, AttributeError):
                            score_val = 0.0

                        job = Job(
                            title=role,
                            company=company,
                            platform="merged",
                            match_score=score_val * 20,  # 转 0-100
                        )
                        db.save_job(job)
                        result["merged"] += 1

        except Exception as e:
            result["errors"].append({"file": fname, "error": str(e)})

    return result
