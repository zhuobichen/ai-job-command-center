"""Tests for job_hunt.db.database module."""

import pytest
from job_hunt.db.database import Database
from job_hunt.models.job import Job


class TestDatabase:
    def test_database_creation(self, temp_db):
        db = Database(str(temp_db))
        assert db.db_path == str(temp_db)

    def test_save_and_get_resume(self, temp_db, sample_resume):
        db = Database(str(temp_db))
        rid = db.save_resume(sample_resume)
        assert rid > 0

        r = db.get_resume()
        assert r is not None
        assert r.name == "Test User"

    def test_save_and_get_job(self, temp_db, sample_job):
        db = Database(str(temp_db))
        jid = db.save_job(sample_job)
        assert jid > 0

        jobs = db.get_jobs(limit=10)
        assert len(jobs) == 1
        assert jobs[0].title == "Python Dev"

    def test_get_jobs_with_city_filter(self, temp_db, sample_job):
        db = Database(str(temp_db))
        db.save_job(sample_job)

        jobs = db.get_jobs(city="南宁")
        assert len(jobs) == 1

        jobs = db.get_jobs(city="广州")
        assert len(jobs) == 0

    def test_update_job_match(self, temp_db, sample_job):
        db = Database(str(temp_db))
        jid = db.save_job(sample_job)
        db.update_job_match(jid, 85.0, '{"match": "good"}')

        job = db.get_job_by_id(jid)
        assert job.match_score == 85.0

    def test_save_application(self, temp_db, sample_job, sample_resume):
        db = Database(str(temp_db))
        db.save_resume(sample_resume)
        jid = db.save_job(sample_job)

        from job_hunt.models.application import Application
        app = Application(job_id=jid, job_title=sample_job.title, company=sample_job.company)
        aid = db.save_application(app)
        assert aid > 0

    def test_application_stats(self, temp_db, sample_job, sample_resume):
        db = Database(str(temp_db))
        db.save_resume(sample_resume)
        jid = db.save_job(sample_job)

        from job_hunt.models.application import Application
        app = Application(job_id=jid, status="applied")
        db.save_application(app)

        stats = db.get_application_stats()
        assert stats["total"] == 1
        assert stats["applied"] == 1

    def test_job_count(self, temp_db, sample_job):
        db = Database(str(temp_db))
        assert db.get_job_count() == 0
        db.save_job(sample_job)
        assert db.get_job_count() == 1

    def test_get_jobs_limit_offset(self, temp_db):
        db = Database(str(temp_db))
        from job_hunt.models.job import Job
        for i in range(20):
            job = Job(title=f"Job {i}", company="Test", city="南宁", platform="gxrc")
            db.save_job(job)

        jobs = db.get_jobs(limit=5, offset=0)
        assert len(jobs) == 5

        jobs = db.get_jobs(limit=5, offset=10)
        assert len(jobs) == 5

    def test_get_jobs_multi_city_query(self, temp_db):
        """回归测试：逗号分隔的多城市查询应匹配任一城市"""
        db = Database(str(temp_db))
        from job_hunt.models.job import Job
        db.save_job(Job(title="Job A", company="C", city="南宁", platform="gxrc"))
        db.save_job(Job(title="Job B", company="C", city="广州", platform="gxrc"))
        db.save_job(Job(title="Job C", company="C", city="桂林", platform="gxrc"))

        # 单城市
        assert len(db.get_jobs(city="南宁")) == 1
        # 多城市（逗号分隔）应匹配南宁+广州，不含桂林
        multi = db.get_jobs(city="南宁,广州")
        assert len(multi) == 2
        titles = {j.title for j in multi}
        assert "Job A" in titles
        assert "Job B" in titles
        assert "Job C" not in titles
        # 中文逗号也支持
        assert len(db.get_jobs(city="南宁，广州")) == 2
