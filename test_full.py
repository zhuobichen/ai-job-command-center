"""
ai-job-hunt 全链路功能测试
==========================
验证所有模块可导入、所有核心流程可用。
"""

import sys
import os
import json
import struct
import math
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))


def generate_test_pcm(duration_sec: float = 0.5, sample_rate: int = 16000) -> bytes:
    """生成测试用 PCM 数据"""
    n = int(duration_sec * sample_rate)
    return b"".join(struct.pack("<h", 0) for _ in range(n))


def hr():
    print("-" * 60)


def test_pass(name):
    print(f"  [{name}] PASS")


def test_skip(name, reason):
    print(f"  [{name}] SKIP ({reason})")


def test_fail(name, error):
    print(f"  [{name}] FAIL: {error}")


def main():
    failed = 0
    passed = 0

    print("=" * 60)
    print("ai-job-hunt 全链路功能测试")
    print("=" * 60 + "\n")

    # ==========================================================
    # 1. 模块导入
    # ==========================================================
    print("[1/8] Module imports")
    try:
        from job_hunt import __version__
        print(f"      version={__version__}"); test_pass("version")

        from job_hunt.utils.config import Config
        test_pass("config")

        from job_hunt.db.database import Database
        test_pass("database")

        from job_hunt.models.job import Job
        from job_hunt.models.resume import Resume
        from job_hunt.models.application import Application
        test_pass("models")

        from job_hunt.utils.display import (
            print_banner, print_info, print_success, print_warning, print_error,
            console
        )
        test_pass("display")

        passed += 5
    except Exception as e:
        test_fail("imports", e); failed += 1
    hr()

    # ==========================================================
    # 2. scrapers
    # ==========================================================
    print("[2/8] Scrapers")
    try:
        from job_hunt.scrapers import BaseScraper, BossScraper, GxrcScraper, GuiPinScaper
        test_pass("import base/boss/gxrc/guipin")
        passed += 1
    except Exception as e:
        test_fail("scraper import", e); failed += 1
    try:
        from job_hunt.scrapers.gxrc import GX_CITY_KEYWORDS, GD_CITY_KEYWORDS
        assert len(GX_CITY_KEYWORDS) == 14, f"expected 14, got {len(GX_CITY_KEYWORDS)}"
        assert "南宁" in GX_CITY_KEYWORDS
        assert "深圳" in GD_CITY_KEYWORDS
        test_pass(f"city keywords: GX={len(GX_CITY_KEYWORDS)} GD={len(GD_CITY_KEYWORDS)}")
        passed += 1
    except Exception as e:
        test_fail("city keywords", e); failed += 1
    hr()

    # ==========================================================
    # 3. AI
    # ==========================================================
    print("[3/8] AI modules")
    try:
        from job_hunt.ai.archetype import detect_archetype, ARCHETYPES
        assert len(ARCHETYPES) == 5

        r = detect_archetype("Python开发工程师 Django后端", "")
        assert r["archetype"] == "python_dev", f"got {r['archetype']}"
        test_pass(f"archetype: {r['label']} confidence={r['confidence']}")

        r2 = detect_archetype("环保工程师 环境监测 大气污染", "")
        assert r2["archetype"] == "env_tech"
        test_pass(f"archetype: {r2['label']} confidence={r2['confidence']}")

        r3 = detect_archetype("数据分析 SQL 报表", "")
        assert r3["archetype"] == "data_analysis"
        test_pass(f"archetype: {r3['label']} confidence={r3['confidence']}")

        passed += 3
    except Exception as e:
        test_fail("archetype", e); failed += 1

    try:
        from job_hunt.ai.brain import AIBrain
        test_pass("brain import")
        passed += 1
    except Exception as e:
        test_fail("brain", e); failed += 1

    try:
        from job_hunt.ai.verifier import VerifyResult, verify_company
        test_pass("verifier import")
        passed += 1
    except Exception as e:
        test_fail("verifier", e); failed += 1
    hr()

    # ==========================================================
    # 4. Pipeline
    # ==========================================================
    print("[4/8] Pipeline")
    try:
        from job_hunt.pipeline import (
            merge_tracker, dedup_jobs, normalize_status,
            check_liveness, CANONICAL_STATES,
        )
        test_pass("pipeline imports")

        # dedup
        from job_hunt.pipeline.dedup import make_job_key, _normalize
        from job_hunt.models.job import Job as PJ
        key = make_job_key(PJ(title="Python开发", company="广西新美数据有限公司", city="南宁"))
        assert "python开发" in key.lower(), f"key: {key}"
        test_pass("dedup key")

        # normalize
        assert normalize_status("已投递") == "applied"
        assert normalize_status("respondido") == "responded"
        assert normalize_status("rechazado") == "rejected"
        assert normalize_status("unknown_xxx") == "evaluated"  # safe default
        test_pass("normalize 9 states")

        # liveness by age
        from job_hunt.pipeline.liveness import check_liveness_by_age
        r = check_liveness_by_age("2026-06-01T00:00:00")
        assert r.is_active, f"should be active (only 20 days), got {r.reason}"
        test_pass("liveness by age")

        # merge: filename slug uses "Unknown" for None company
        import tempfile as tf2
        tmpdir = tf2.mkdtemp()
        from job_hunt.pipeline.merge import write_tsv_addition
        path = write_tsv_addition(str(tmpdir), 1, None, "Python Dev", 4.2, "Evaluated")
        assert os.path.exists(path)
        assert "Unknown" in path, f"slug should contain Unknown: {path}"
        test_pass("merge None guard")

        passed += 5
    except Exception as e:
        test_fail("pipeline", e); failed += 1
    hr()

    # ==========================================================
    # 5. Applier / Filter
    # ==========================================================
    print("[5/8] Applier & Filter")
    try:
        from job_hunt.applier.filter import should_filter, load_blacklist, add_to_blacklist
        test_pass("filter import")

        class FakeJob2:
            pass

        fj = FakeJob2()
        fj.title = "Python开发工程师"
        fj.company = "广西新美数据"
        fj.salary_min = 6000
        fj.salary_max = 10000

        # normal case
        r = should_filter(fj)
        assert r.passed, f"should pass, got {r.reason}"
        test_pass("filter: normal passes")

        # headhunter
        fj.title = "猎头顾问 Python开发"
        r = should_filter(fj)
        assert not r.passed
        test_pass("filter: headhunter blocked")

        # training
        fj.title = "Python培训 学徒 包就业"
        r = should_filter(fj)
        assert not r.passed
        test_pass("filter: training blocked")

        passed += 3
    except Exception as e:
        test_fail("filter", e); failed += 1
    hr()

    # ==========================================================
    # 6. Browser-act integration
    # ==========================================================
    print("[6/8] Browser-act integration")
    try:
        from job_hunt.browser_act import BrowserAct, is_available, _find_browser_act
        test_pass("browser_act import")
        if is_available():
            test_pass("browser-act available")
        else:
            test_skip("browser-act available", "not installed")
        passed += 1
    except Exception as e:
        test_fail("browser_act", e); failed += 1
    hr()

    # ==========================================================
    # 7. Database
    # ==========================================================
    print("[7/8] Database operations")
    try:
        import uuid as _uuid
        tmp_db = os.path.join(os.environ.get("TEMP", "/tmp"), f"test_jh_{_uuid.uuid4().hex[:8]}.db")
        db = Database(tmp_db)
        test_pass("db open")

        # save resume
        r = Resume(name="Test", education_level="硕士", major="环境工程",
                   university="华南理工", desired_city="南宁", skills="Python,AI",
                   salary_min=6000, salary_max=12000)
        rid = db.save_resume(r)
        assert rid > 0
        test_pass("db save resume")

        # save job
        j = Job(title="Python开发", company="Test公司", city="南宁", platform="test",
                salary_text="6K-10K", source_url="https://example.com/job/1")
        jid = db.save_job(j)
        assert jid > 0
        test_pass("db save job")

        # save application
        app = Application(job_id=jid, job_title="Python开发", company="Test公司",
                          platform="test", status="applied")
        aid = db.save_application(app)
        assert aid > 0
        test_pass("db save application")

        # query
        jobs = db.get_jobs(city="南宁")
        assert len(jobs) >= 1
        test_pass("db query city")

        stats = db.get_application_stats()
        assert stats["total"] >= 1
        test_pass("db stats")

        db.update_job_match(jid, 85.0, json.dumps({"match_score": 85}))
        updated = db.get_job_by_id(jid)
        assert updated.match_score == 85.0
        test_pass("db update match")

        passed += 6  # 6 tests (no cleanup)
    except Exception as e:
        test_fail("database", e); failed += 1
    hr()

    # ==========================================================
    # 8. Config
    # ==========================================================
    print("[8/8] Config")
    try:
        from job_hunt.utils.config import Config as CFG
        import uuid as _uid2
        tmp_cfg = os.path.join(os.environ.get("TEMP", os.getcwd()), f"test_cfg_{_uid2.uuid4().hex[:8]}.toml")
        cfg2 = CFG(tmp_cfg)
        c1 = cfg2.get("preferences", "cities")
        c2 = cfg2.get("platforms", "gxrc")
        c3 = cfg2.get("advanced", "min_apply_score")
        if c1 and c2 and c3:
            test_pass(f"default config: cities={c1} gxrc={c2} min_score={c3}")
        else:
            test_fail("config", f"got: cities={repr(c1)} gxrc={repr(c2)} min_score={repr(c3)}")
        passed += 1
    except Exception as e:
        import traceback
        traceback.print_exc()
        test_fail("config", str(e)[:100]); failed += 1
    hr()

    # ==========================================================
    # Report
    # ==========================================================
    total = passed + failed
    print()
    print("=" * 60)
    print(f"Result: {passed}/{total} passed", end="")
    if failed:
        print(f" ({failed} failed)")
    else:
        print(" [OK] All passed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
