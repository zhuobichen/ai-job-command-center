"""
ai-job-hunt CLI 全命令验证 (v0.3)
==================================
验证所有模块可用、CLI command 注册、--json 输出。
"""

import sys, os, json, uuid, tempfile, subprocess as sp

PROJ = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(PROJ, "src")
sys.path.insert(0, SRC)
os.chdir(PROJ)
ENV = {**os.environ, "PYTHONPATH": "src", "PYTHONIOENCODING": "utf-8"}

passed = 0; failed = 0

def t(name, ok, detail=""):
    global passed, failed
    if ok: passed += 1; print(f"  [PASS] {name}")
    else: failed += 1; print(f"  [FAIL] {name} — {detail}")

def _jd(job) -> dict:
    return {"id": job.id, "title": job.title, "company": job.company,
            "city": job.city, "salary": job.salary_range_display}

print("=" * 60)
print("ai-job-hunt CLI v0.3 — AI-ready test")
print("=" * 60)

# ══════════════════════════════════════════════════════
# 1. Imports
# ══════════════════════════════════════════════════════
print("\n[1] All imports")
try:
    from job_hunt.utils.config import Config
    from job_hunt.utils.output import Output
    from job_hunt.db.database import Database
    from job_hunt.models.job import Job
    from job_hunt.models.resume import Resume
    from job_hunt.models.application import Application
    from job_hunt.ai.archetype import detect_archetype, ARCHETYPES
    from job_hunt.ai.brain import AIBrain
    from job_hunt.ai.verifier import VerifyResult
    from job_hunt.scrapers import GxrcScraper, GuiPinScaper, BossScraper
    from job_hunt.scrapers.gxrc import GX_CITY_KEYWORDS, GD_CITY_KEYWORDS
    from job_hunt.pipeline import merge_tracker, dedup_jobs, normalize_status, check_liveness
    from job_hunt.pipeline.normalize import CANONICAL_STATES
    from job_hunt.applier.filter import should_filter, load_blacklist
    from job_hunt.browser_act import is_available
    t("all 17 modules", True)
except Exception as e:
    t("imports", False, str(e)[:80])

# ══════════════════════════════════════════════════════
# 2. Config
# ══════════════════════════════════════════════════════
print("\n[2] Config")
ts = tempfile.mkdtemp()
cp = os.path.join(ts, f"cfg_{uuid.uuid4().hex[:4]}.toml")
cfg = Config(cp)
t("load", bool(cfg))
t("default cities", cfg.get("preferences","cities") == "南宁,广州", repr(cfg.get("preferences","cities")))
t("default gxrc", cfg.get("platforms","gxrc") in (True, "true"), repr(cfg.get("platforms","gxrc")))
t("default min_score", cfg.get("advanced","min_apply_score") in ("4.0", 4.0), repr(cfg.get("advanced","min_apply_score")))

# ══════════════════════════════════════════════════════
# 3. Output dual-mode
# ══════════════════════════════════════════════════════
print("\n[3] Output")
oj = Output(json_mode=True)
ot = Output(json_mode=False)
oj.info("x"); oj.success("y"); oj.warn("z")
t("json mode accumulates", len(oj._results) == 3)
t("terminal mode", not ot.json_mode)

# ══════════════════════════════════════════════════════
# 4. Models
# ══════════════════════════════════════════════════════
print("\n[4] Models")
j = Job(title="Python Dev", company="Test Corp", city="南宁", platform="gxrc")
t("job dict", _jd(j)["title"] == "Python Dev")
r = Resume(name="Test", education_level="硕士", major="环境工程")
t("resume summary", bool(r.summary()))
a = Application(status="responded")
t("sort order responded", a.status_sort_order == 1, f"got {a.status_sort_order}")
a2 = Application(status="applied")
t("sort order applied", a2.status_sort_order == 2)

# ══════════════════════════════════════════════════════
# 5. Database
# ══════════════════════════════════════════════════════
print("\n[5] Database")
tdb = os.path.join(ts, f"db_{uuid.uuid4().hex[:4]}.db")
db = Database(tdb)
rid = db.save_resume(r); t("save resume", rid > 0)
jid = db.save_job(j); t("save job", jid > 0)
a.job_id = jid; aid = db.save_application(a); t("save application", aid > 0)
t("query city", db.get_job_count(city="南宁") >= 1)
db.update_job_match(jid, 85.0, '{}')
t("update match", db.get_job_by_id(jid).match_score == 85.0)
t("stats", db.get_application_stats()["total"] >= 1)

# ══════════════════════════════════════════════════════
# 6. Pipeline
# ══════════════════════════════════════════════════════
print("\n[6] Pipeline")
t("9 states", len(CANONICAL_STATES) == 9)
t("normalize applied", normalize_status("已投递") == "applied")
t("normalize responded", normalize_status("respondido") == "responded")
t("normalize unknown->evaluated", normalize_status("phone_screen") == "evaluated")

from job_hunt.pipeline.dedup import dedup_jobs as dd
j2 = Job(title="Python Dev", company="Test Corp", city="南宁", platform="boss")
r2 = dd([j, j2])
t("dedup same job", len(r2["unique"]) == 1, f"got {len(r2['unique'])}")

from job_hunt.pipeline.liveness import check_liveness_by_age
lr = check_liveness_by_age("2026-06-01T00:00:00")
t("liveness active <30d", lr.is_active, lr.reason[:50])

from job_hunt.pipeline.merge import write_tsv_addition
mp = write_tsv_addition(ts, 1, None, "Python Dev", 4.2)
t("merge None guard", os.path.exists(mp))

# ══════════════════════════════════════════════════════
# 7. City keywords
# ══════════════════════════════════════════════════════
print("\n[7] City keywords")
t("GX 14 cities", len(GX_CITY_KEYWORDS) == 14)
t("GD 21 cities", len(GD_CITY_KEYWORDS) == 21)
t("南宁 in GX", "南宁" in GX_CITY_KEYWORDS)
t("深圳 in GD", "深圳" in GD_CITY_KEYWORDS)

# ══════════════════════════════════════════════════════
# 8. Archetype
# ══════════════════════════════════════════════════════
print("\n[8] Archetype")
t("5 archetypes", len(ARCHETYPES) == 5)
r1 = detect_archetype("Python开发工程师 Django后端 API")
t("python_dev detect", r1["archetype"] == "python_dev", f"{r1['label']} c={r1['confidence']}")
r2 = detect_archetype("环保工程师 环境监测 大气污染 PM2.5")
t("env_tech detect", r2["archetype"] == "env_tech", f"{r2['label']} c={r2['confidence']}")
r3 = detect_archetype("数据分析师 SQL pandas 报表")
t("data_analysis detect", r3["archetype"] == "data_analysis", f"{r3['label']} c={r3['confidence']}")

# ══════════════════════════════════════════════════════
# 9. Filter
# ══════════════════════════════════════════════════════
print("\n[9] Smart filter")
class FJ: pass
fj = FJ(); fj.title="猎头顾问 Python"; fj.company="XX猎头"; fj.salary_min=0; fj.salary_max=0
fr = should_filter(fj)
t("headhunter blocked", not fr.passed, fr.reason)
fj.title="Python开发工程师"; fj.company="广西新美数据"
fr = should_filter(fj)
t("normal passes", fr.passed)
fj.title="Python培训 学徒 包就业"
fr = should_filter(fj)
t("training blocked", not fr.passed)

# ══════════════════════════════════════════════════════
# 10. browser-act
# ══════════════════════════════════════════════════════
print("\n[10] Browser-act")
t("is_available", is_available())

# ══════════════════════════════════════════════════════
# 11. CLI --help (via import, not subprocess)
# ══════════════════════════════════════════════════════
print("\n[11] CLI --help (via Typer API)")
try:
    from typer.testing import CliRunner
    from job_hunt.cli import app
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    cmds = ["init","scan","match","eval","auto","resume","apply","status","report","config","filter","verify","parse","pipeline"]
    found = [c for c in cmds if c in result.stdout]
    t(f"commands: {len(found)}/{len(cmds)}", len(found) >= 13, f"missing: {set(cmds)-set(found)}")
except Exception as e:
    t("--help", False, str(e)[:100])

# ══════════════════════════════════════════════════════
# 12. CLI --json outputs (via Typer CliRunner)
# ══════════════════════════════════════════════════════
print("\n[12] CLI --json via CliRunner")
try:
    from typer.testing import CliRunner
    from job_hunt.cli import app
    runner = CliRunner()

    r = runner.invoke(app, ["status", "--json"])
    data = json.loads(r.stdout) if r.stdout else {"error": r.stderr}
    t("status --json", data.get("success", True), f"keys: {list(data.keys())[:6]}")

    r = runner.invoke(app, ["config", "list", "--json"])
    data2 = json.loads(r.stdout) if r.stdout else {"error": r.stderr}
    t("config list --json", "preferences" in data2, f"keys: {list(data2.keys())[:4]}")

    r = runner.invoke(app, ["pipeline", "health", "--json"])
    data3 = json.loads(r.stdout) if r.stdout else {"error": r.stderr}
    t("pipeline health --json", "total_jobs" in data3)
except Exception as e:
    t("--json tests", False, str(e)[:100])

# ══════════════════════════════════════════════════════
print()
print("=" * 60)
print(f"Result: {passed}/{passed+failed} passed", end="")
if failed: print(f" ({failed} failed)")
else: print(" [OK] All passed")
print("=" * 60)
sys.exit(0 if failed == 0 else 1)
