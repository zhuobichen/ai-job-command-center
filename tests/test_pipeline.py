"""Tests for job_hunt.pipeline modules."""

import pytest
from datetime import datetime, timedelta

from job_hunt.models.job import Job
from job_hunt.pipeline.normalize import (
    normalize_status,
    CANONICAL_STATES,
    get_state_label,
    get_state_group,
    get_status_sort_order,
    validate_pipeline,
)
from job_hunt.pipeline.dedup import dedup_jobs, find_cross_platform_duplicates


class TestNormalizeStatus:
    def test_normalize_evaluated(self):
        assert normalize_status("evaluated") == "evaluated"
        assert normalize_status("已评估") == "evaluated"

    def test_normalize_applied(self):
        assert normalize_status("applied") == "applied"
        assert normalize_status("已投递") == "applied"
        assert normalize_status("投递") == "applied"

    def test_normalize_responded(self):
        assert normalize_status("responded") == "responded"
        assert normalize_status("已回复") == "responded"

    def test_normalize_interview(self):
        assert normalize_status("interview") == "interview"
        assert normalize_status("面试中") == "interview"

    def test_normalize_rejected(self):
        assert normalize_status("rejected") == "rejected"
        assert normalize_status("已拒绝") == "rejected"

    def test_normalize_unknown_defaults_to_evaluated(self):
        assert normalize_status("unknown_status") == "evaluated"
        assert normalize_status("phone_screen") == "evaluated"

    def test_canonical_states_count(self):
        assert len(CANONICAL_STATES) == 9


class TestGetStateHelpers:
    def test_get_state_label(self):
        assert get_state_label("applied") == "Applied"
        assert get_state_label("interview") == "Interview"

    def test_get_state_group(self):
        assert get_state_group("applied") == "applied"
        assert get_state_group("rejected") == "rejected"

    def test_get_status_sort_order(self):
        assert get_status_sort_order("interview") == 0
        assert get_status_sort_order("responded") == 1
        assert get_status_sort_order("applied") == 2


class TestDedup:
    def test_dedup_identical_jobs(self):
        j1 = Job(title="Python Dev", company="Test Corp", city="南宁", platform="gxrc")
        j2 = Job(title="Python Dev", company="Test Corp", city="南宁", platform="gxrc")
        result = dedup_jobs([j1, j2])
        assert len(result["unique"]) == 1

    def test_dedup_different_jobs(self):
        j1 = Job(title="Python Dev", company="Test Corp", city="南宁", platform="gxrc")
        j2 = Job(title="Java Dev", company="Test Corp", city="南宁", platform="gxrc")
        result = dedup_jobs([j1, j2])
        assert len(result["unique"]) == 2

    def test_find_cross_platform_duplicates(self):
        j1 = Job(title="Python Dev", company="Test Corp", city="南宁", platform="gxrc")
        j2 = Job(title="Python Dev", company="Test Corp", city="南宁", platform="boss")
        result = find_cross_platform_duplicates([j1, j2])
        assert len(result) >= 1


class TestValidatePipeline:
    def test_validate_empty_pipeline(self, configured_db):
        result = validate_pipeline(configured_db)
        assert result["total_jobs"] >= 0
        assert result["total_applications"] >= 0
        assert isinstance(result["orphan_applications"], list)
        assert isinstance(result["stale_jobs"], list)
