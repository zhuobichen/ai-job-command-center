"""调试匹配引擎，看每个岗位的分数"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from job_hunt.db.database import Database
from job_hunt.ai.matcher import KeywordMatcher

db = Database()
resume = db.get_resume()
if not resume:
    print("无简历，请先运行 scripts/load_resume.py")
    sys.exit(1)

print(f"简历: {resume.summary()}")
print(f"简历技能: {resume.skills}")

# 用简历技能初始化匹配器
matcher = KeywordMatcher()
matcher.skills = [s.strip().lower() for s in (resume.skills or "").split(",") if s.strip()] or matcher.skills
print(f"匹配器技能: {matcher.skills}")
print()

# 对所有岗位打分
jobs = db.get_jobs(limit=50, active_only=True)
print(f"数据库共 {len(jobs)} 个岗位\n")
print(f"{'岗位':<25} {'公司':<18} {'分数':>6} {'建议':<10}")
print("-" * 70)

for job in jobs:
    r = matcher.match(job.to_dict())
    score = r.get("match_score", 0)
    suggestion = r.get("suggestions", "")
    reasons = r.get("reasons", [])
    gaps = r.get("gaps", [])
    print(f"{job.title[:24]:<25} {job.company[:17]:<18} {score:>6} {suggestion:<10}")
    if reasons:
        print(f"    reasons: {reasons}")
    if gaps:
        print(f"    gaps: {gaps}")
    print()
