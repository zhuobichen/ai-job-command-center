"""Tests for job_hunt.ai modules."""

import pytest
from job_hunt.ai.archetype import detect_archetype, ARCHETYPES, get_proof_point_priority
from job_hunt.ai.matcher import KeywordMatcher


class TestArchetype:
    def test_archetypes_count(self):
        assert len(ARCHETYPES) == 5

    def test_detect_python_dev(self):
        result = detect_archetype("Python开发工程师 Django后端 API")
        assert result["archetype"] == "python_dev"
        assert result["confidence"] >= 0.5

    def test_detect_data_analysis(self):
        result = detect_archetype("数据分析师 SQL pandas 报表")
        assert result["archetype"] == "data_analysis"
        assert result["confidence"] >= 0.3

    def test_detect_env_tech(self):
        result = detect_archetype("环保工程师 环境监测 大气污染 PM2.5")
        assert result["archetype"] == "env_tech"
        assert result["confidence"] >= 0.2

    def test_detect_ai_info(self):
        result = detect_archetype("AI工程师 LLM 机器学习 深度学习")
        assert result["archetype"] == "ai_informatization"
        assert result["confidence"] >= 0.2

    def test_detect_gov_inst(self):
        result = detect_archetype("事业单位 计算机岗 事业编")
        assert result["archetype"] == "government"
        assert result["confidence"] >= 0.1

    def test_get_proof_point_priority(self):
        priority = get_proof_point_priority("python_dev")
        assert isinstance(priority, list)
        assert len(priority) > 0


class TestKeywordMatcher:
    def test_matcher_creation(self):
        matcher = KeywordMatcher()
        assert matcher is not None

    def test_match_with_keywords(self):
        matcher = KeywordMatcher()
        job = {
            "title": "Python开发工程师",
            "company": "Test Corp",
            "city": "南宁",
            "description": "熟悉Django Flask FastAPI",
            "requirements": "3年经验",
        }
        result = matcher.match(job)
        assert "match_score" in result
        assert isinstance(result["match_score"], (int, float))

    def test_evaluate_with_keywords(self):
        matcher = KeywordMatcher()
        job = {
            "title": "Python开发工程师",
            "company": "Test Corp",
            "city": "南宁",
            "description": "熟悉Django Flask FastAPI",
            "requirements": "3年经验",
        }
        result = matcher.evaluate(job)
        assert "overall_score" in result or "match_score" in result
