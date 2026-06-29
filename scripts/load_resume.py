"""手动存入简历数据（模拟无 API key 场景下的简历导入）"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from job_hunt.db.database import Database
from job_hunt.models.resume import Resume

# 读取简历原文
with open("data/cv.md", "r", encoding="utf-8") as f:
    raw = f.read()

# 手动构造结构化简历（模拟 AI 解析结果）
r = Resume(
    name="陈立志",
    phone="138-xxxx-1234",
    email="chenlizhi@example.com",
    wechat="chenlizhi_env",
    education_level="本科",
    university="广西大学",
    major="环境工程",
    graduation_year=2026,
    projects="南宁市PM2.5时空分布特征研究|校园空气质量实时监测系统|某化工园区环境影响评价实习",
    skills="Python,pandas,numpy,matplotlib,SQL,Flask,SQLite,Git,Linux,ArcGIS,AERMOD,环境监测,环评报告,AQI数据分析,PM2.5源解析",
    work_years=1,
    desired_city="南宁,广州",
    desired_position="环境工程师,数据分析,Python开发",
    desired_industry="环保/环境监测/信息化",
    salary_min=6000,
    salary_max=12000,
    raw_text=raw[:5000],
    raw_file_path="data/cv.md",
)

db = Database()
rid = db.save_resume(r)
print(f"简历已存入数据库, id={rid}")
print(f"简历摘要: {r.summary()}")
