"""Tests for job_hunt.models modules."""

import pytest
from job_hunt.models.job import Job
from job_hunt.models.resume import Resume
from job_hunt.models.application import Application


class TestJob:
    def test_job_creation(self):
        job = Job(title="Python Dev", company="Test Corp", city="南宁", platform="gxrc")
        assert job.title == "Python Dev"
        assert job.company == "Test Corp"
        assert job.city == "南宁"
        assert job.platform == "gxrc"

    def test_job_salary_range_display(self, sample_job):
        assert "8000" in sample_job.salary_range_display or "8" in sample_job.salary_range_display

    def test_job_to_dict(self, sample_job):
        d = sample_job.to_dict()
        assert d["title"] == "Python Dev"
        assert d["company"] == "Test Corp"


class TestResume:
    def test_resume_creation(self):
        r = Resume(
            name="Test",
            education_level="硕士",
            major="环境工程"
        )
        assert r.name == "Test"
        assert r.education_level == "硕士"
        assert r.major == "环境工程"

    def test_resume_summary(self, sample_resume):
        s = sample_resume.summary()
        assert isinstance(s, str)
        assert len(s) > 0

    def test_resume_to_dict(self, sample_resume):
        d = sample_resume.to_dict()
        assert d["name"] == "Test User"
        assert d["education_level"] == "硕士"


class TestApplication:
    def test_application_creation(self):
        a = Application(status="applied")
        assert a.status == "applied"

    def test_sort_order_interview(self):
        a = Application(status="interview")
        assert a.status_sort_order == 0

    def test_sort_order_responded(self):
        a = Application(status="responded")
        assert a.status_sort_order == 1

    def test_sort_order_applied(self):
        a = Application(status="applied")
        assert a.status_sort_order == 2

    def test_sort_order_rejected(self):
        a = Application(status="rejected")
        assert a.status_sort_order == 5

    def test_application_to_dict(self, sample_application):
        d = sample_application.to_dict()
        assert "status" in d
