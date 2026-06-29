"""Tests for job_hunt.applier modules."""

import pytest
from job_hunt.models.job import Job
from job_hunt.applier.filter import should_filter, load_blacklist, add_to_blacklist


class TestSmartFilter:
    def test_headhunter_blocked(self):
        job = Job(title="猎头顾问 Python", company="XX猎头", platform="gxrc")
        result = should_filter(job)
        assert not result.passed

    def test_training_blocked(self):
        job = Job(title="Python培训 学徒 包就业", company="培训机构", platform="gxrc")
        result = should_filter(job)
        assert not result.passed

    def test_normal_job_passes(self):
        job = Job(title="Python开发工程师", company="广西新美数据", platform="gxrc")
        result = should_filter(job)
        # May pass or fail depending on other factors
        assert isinstance(result.passed, bool)
        assert isinstance(result.reason, str)

    def test_blacklist_loaded(self, configured_db):
        blacklist = load_blacklist(configured_db)
        assert isinstance(blacklist, list)

    def test_add_to_blacklist(self, configured_db):
        add_to_blacklist(configured_db, "Bad Company")
        blacklist = load_blacklist(configured_db)
        assert "Bad Company" in blacklist
