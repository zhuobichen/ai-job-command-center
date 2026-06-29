"""SQLite数据库操作模块"""

import sqlite3
import json
import os
import re
from typing import Optional
from datetime import datetime

from ..models.resume import Resume
from ..models.job import Job
from ..models.application import Application


class Database:
    """本地SQLite数据库管理"""

    def __init__(self, db_path: str = "data/resume.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_tables(self):
        """初始化数据库表"""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS resumes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    wechat TEXT,
                    desired_city TEXT DEFAULT '',
                    desired_position TEXT DEFAULT '',
                    desired_industry TEXT DEFAULT '',
                    salary_min INTEGER DEFAULT 0,
                    salary_max INTEGER DEFAULT 0,
                    education_level TEXT DEFAULT '',
                    university TEXT DEFAULT '',
                    major TEXT DEFAULT '',
                    graduation_year INTEGER DEFAULT 0,
                    projects TEXT DEFAULT '',
                    skills TEXT DEFAULT '',
                    work_years INTEGER DEFAULT 0,
                    raw_text TEXT DEFAULT '',
                    raw_file_path TEXT DEFAULT '',
                    created_at TEXT DEFAULT '',
                    updated_at TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT DEFAULT '',
                    company TEXT DEFAULT '',
                    city TEXT DEFAULT '',
                    district TEXT DEFAULT '',
                    salary_min INTEGER DEFAULT 0,
                    salary_max INTEGER DEFAULT 0,
                    salary_text TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    requirements TEXT DEFAULT '',
                    tags TEXT DEFAULT '',
                    experience TEXT DEFAULT '',
                    education TEXT DEFAULT '',
                    benefits TEXT DEFAULT '',
                    platform TEXT DEFAULT '',
                    source_url TEXT DEFAULT '',
                    source_id TEXT DEFAULT '',
                    match_score REAL DEFAULT 0.0,
                    match_detail TEXT DEFAULT '',
                    eval_score TEXT DEFAULT '',
                    eval_detail TEXT DEFAULT '',
                    recommend_reason TEXT DEFAULT '',
                    is_active INTEGER DEFAULT 1,
                    is_deleted INTEGER DEFAULT 0,
                    scraped_at TEXT DEFAULT '',
                    created_at TEXT DEFAULT ''
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source 
                    ON jobs(platform, source_id) WHERE source_id != '';

                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    job_title TEXT DEFAULT '',
                    company TEXT DEFAULT '',
                    platform TEXT DEFAULT '',
                    status TEXT DEFAULT 'applied',
                    applied_at TEXT DEFAULT '',
                    replied_at TEXT,
                    interview_at TEXT,
                    greeting TEXT DEFAULT '',
                    resume_path TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    interview_type TEXT DEFAULT '',
                    interview_notes TEXT DEFAULT '',
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT DEFAULT ''
                );
            """)

    # ─── Resume ───────────────────────────────────────────

    def save_resume(self, resume: Resume) -> int:
        resume.updated_at = datetime.now().isoformat()
        with self._connect() as conn:
            # 只保留一条简历记录
            existing = conn.execute("SELECT id FROM resumes LIMIT 1").fetchone()
            if existing:
                fields = resume.to_dict()
                fields["updated_at"] = resume.updated_at
                set_clause = ", ".join(f"{k}=?" for k in fields)
                values = list(fields.values()) + [existing["id"]]
                conn.execute(f"UPDATE resumes SET {set_clause} WHERE id=?", values)
                return existing["id"]
            else:
                fields = resume.to_dict()
                fields["created_at"] = resume.created_at
                fields["updated_at"] = resume.updated_at
                cols = ", ".join(fields.keys())
                placeholders = ", ".join("?" for _ in fields)
                cur = conn.execute(
                    f"INSERT INTO resumes ({cols}) VALUES ({placeholders})",
                    list(fields.values()),
                )
                return cur.lastrowid

    def get_resume(self) -> Optional[Resume]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM resumes ORDER BY updated_at DESC LIMIT 1").fetchone()
            if row:
                return Resume(**{k: row[k] for k in row.keys()})
            return None

    # ─── Jobs ─────────────────────────────────────────────

    def save_job(self, job: Job) -> int:
        """保存岗位，已存在的（同平台+source_id）则更新"""
        with self._connect() as conn:
            # 检查是否已存在
            if job.source_id and job.platform:
                existing = conn.execute(
                    "SELECT id FROM jobs WHERE platform=? AND source_id=?",
                    (job.platform, job.source_id),
                ).fetchone()
                if existing:
                    fields = job.to_dict()
                    set_clause = ", ".join(f"{k}=?" for k in fields)
                    values = list(fields.values()) + [existing["id"]]
                    conn.execute(f"UPDATE jobs SET {set_clause} WHERE id=?", values)
                    return existing["id"]

            fields = job.to_dict()
            fields["created_at"] = job.created_at
            cols = ", ".join(fields.keys())
            placeholders = ", ".join("?" for _ in fields)
            cur = conn.execute(
                f"INSERT INTO jobs ({cols}) VALUES ({placeholders})",
                list(fields.values()),
            )
            return cur.lastrowid

    def get_jobs(
        self,
        limit: int = 50,
        offset: int = 0,
        city: Optional[str] = None,
        platform: Optional[str] = None,
        keyword: Optional[str] = None,
        min_match: float = 0,
        active_only: bool = True,
    ) -> list[Job]:
        conditions = []
        params = []

        if active_only:
            conditions.append("is_active=1 AND is_deleted=0")
        if city:
            # 支持逗号分隔的多城市查询（南宁,广州 → 查询任一匹配）
            cities = [c.strip() for c in re.split(r'[,，、]', city) if c.strip()]
            if len(cities) == 1:
                conditions.append("(city LIKE ? OR district LIKE ?)")
                params.extend([f"%{cities[0]}%", f"%{cities[0]}%"])
            else:
                city_conds = []
                for c in cities:
                    city_conds.append("(city LIKE ? OR district LIKE ?)")
                    params.extend([f"%{c}%", f"%{c}%"])
                conditions.append("(" + " OR ".join(city_conds) + ")")
        if platform:
            conditions.append("platform=?")
            params.append(platform)
        if keyword:
            conditions.append("(title LIKE ? OR description LIKE ? OR company LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if min_match > 0:
            conditions.append("match_score >= ?")
            params.append(min_match)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM jobs WHERE {where} ORDER BY match_score DESC, scraped_at DESC LIMIT ? OFFSET ?",
                params,
            ).fetchall()

        return [Job(**{k: row[k] for k in row.keys()}) for row in rows]

    def get_job_count(self, city: Optional[str] = None, platform: Optional[str] = None) -> int:
        conditions = ["is_active=1 AND is_deleted=0"]
        params = []
        if city:
            conditions.append("(city LIKE ? OR district LIKE ?)")
            params.extend([f"%{city}%", f"%{city}%"])
        if platform:
            conditions.append("platform=?")
            params.append(platform)

        where = " AND ".join(conditions)
        with self._connect() as conn:
            row = conn.execute(f"SELECT COUNT(*) as cnt FROM jobs WHERE {where}", params).fetchone()
            return row["cnt"] if row else 0

    def get_job_by_id(self, job_id: int) -> Optional[Job]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row:
                return Job(**{k: row[k] for k in row.keys()})
            return None

    def update_job_match(self, job_id: int, match_score: float, match_detail: str = ""):
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET match_score=?, match_detail=? WHERE id=?",
                (match_score, match_detail, job_id),
            )

    def update_job_eval(self, job_id: int, eval_score: str, eval_detail: str = ""):
        with self._connect() as conn:
            conn.execute(
                "UPDATE jobs SET eval_score=?, eval_detail=? WHERE id=?",
                (eval_score, eval_detail, job_id),
            )

    def delete_jobs(self, job_ids: list[int]) -> int:
        """批量删除岗位"""
        with self._connect() as conn:
            placeholders = ",".join("?" for _ in job_ids)
            cur = conn.execute(f"DELETE FROM jobs WHERE id IN ({placeholders})", job_ids)
            return cur.rowcount

    # ─── Applications ─────────────────────────────────────

    def save_application(self, app: Application) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO applications 
                   (job_id, job_title, company, platform, status, applied_at, 
                    replied_at, interview_at, greeting, resume_path, notes,
                    interview_type, interview_notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    app.job_id, app.job_title, app.company, app.platform,
                    app.status, app.applied_at, app.replied_at, app.interview_at,
                    app.greeting, app.resume_path, app.notes,
                    app.interview_type, app.interview_notes,
                ),
            )
            return cur.lastrowid

    def get_applications(self, limit: int = 50) -> list[Application]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM applications 
                   ORDER BY 
                     CASE status 
                       WHEN 'interview' THEN 0 
                       WHEN 'replied' THEN 1 
                       WHEN 'applied' THEN 2 
                       WHEN 'ignored' THEN 3 
                       WHEN 'rejected' THEN 4 
                       WHEN 'offer' THEN 5 
                     END,
                     applied_at DESC 
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        return [Application(**{k: row[k] for k in row.keys()}) for row in rows]

    def get_application_stats(self) -> dict:
        with self._connect() as conn:
            row = conn.execute("""
                SELECT 
                  COUNT(*) as total,
                  SUM(CASE WHEN status='applied' THEN 1 ELSE 0 END) as applied,
                  SUM(CASE WHEN status='replied' THEN 1 ELSE 0 END) as replied,
                  SUM(CASE WHEN status='interview' THEN 1 ELSE 0 END) as interview,
                  SUM(CASE WHEN status='offer' THEN 1 ELSE 0 END) as offer,
                  SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) as rejected,
                  SUM(CASE WHEN status='ignored' THEN 1 ELSE 0 END) as ignored
                FROM applications
            """).fetchone()
            return dict(row) if row else {}

    def update_application_status(self, app_id: int, status: str, notes: str = ""):
        with self._connect() as conn:
            now = datetime.now().isoformat()
            updates = {"status": status, "notes": notes}
            if status == "replied":
                updates["replied_at"] = now
            elif status == "interview":
                updates["interview_at"] = now
            set_clause = ", ".join(f"{k}=?" for k in updates)
            values = list(updates.values()) + [app_id]
            conn.execute(f"UPDATE applications SET {set_clause} WHERE id=?", values)

    # ─── Config ───────────────────────────────────────────

    def get_config(self, key: str, default: str = "") -> str:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    def set_config(self, key: str, value: str):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO config (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=?",
                (key, value, value),
            )
