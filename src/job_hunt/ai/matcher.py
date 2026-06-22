"""
无AI关键词匹配引擎
==================
当 litellm/AI 不可用时，用关键词重叠+原型分类做匹配打分。
不需要调用任何 LLM API，纯规则引擎。

匹配维度（模拟 AI match）：
- 技能匹配 40%: 关键词重叠度
- 经验匹配 30%: 原型分类 + 行业吻合度
- 硬性匹配 20%: 学历/年限
- 地点优先 10%: 目标城市加分
"""

import re
from typing import Optional

from .archetype import detect_archetype, ARCHETYPES


# 求职者技能画像（从简历中提取的关键词）
PROFILE_SKILLS = [
    "python", "数据分析", "数据融合", "PM2.5", "AI", "机器学习",
    "深度学习", "自动化", "脚本", "遥感", "GIS", "SQL",
    "环境工程", "大气", "环境监测", "matlab", "pytorch",
    "大模型", "LLM", "agent", "爬虫", "数据可视化",
]

PROFILE_EXPERIENCE = [
    "环境数据处理", "时空数据融合", "大气污染研究",
    "Python开发", "AI工具链", "browser-act自动化",
    "公众号日报自动化", "求职系统开发",
]

TARGET_CITIES = [
    "南宁", "柳州", "桂林", "玉林", "北海", "钦州",
    "梧州", "防城港", "百色", "河池", "贵港", "贺州",
    "来宾", "崇左",  # 广西
    "广州", "深圳", "东莞", "佛山", "珠海", "中山",  # 广东
]

MARKET_SALARY = {
    "南宁": (5000, 10000),
    "柳州": (4500, 9000),
    "广州": (8000, 20000),
    "深圳": (10000, 25000),
    "佛山": (6000, 15000),
    "东莞": (6000, 15000),
    "default": (4000, 12000),
}


class KeywordMatcher:
    """无AI匹配器"""

    def __init__(
        self,
        skills: list = None,
        experience: list = None,
        target_cities: list = None,
        education: str = "硕士",
    ):
        self.skills = [s.lower() for s in (skills or PROFILE_SKILLS)]
        self.experience = [e.lower() for e in (experience or PROFILE_EXPERIENCE)]
        self.target_cities = target_cities or TARGET_CITIES
        self.education = education

    # ─── 主入口 ────────────────────────────────────────

    def match(self, job: dict) -> dict:
        """匹配岗位，返回与 AI match_job 兼容的 dict"""
        title = (job.get("title") or "").lower()
        desc = (job.get("description") or "").lower()
        company = (job.get("company") or "").lower()
        city = (job.get("city") or "")

        # 四维打分
        skill_score = self._skill_match(title, desc, company)
        exp_score = self._experience_match(title, desc, company)
        hard_score = self._hard_match(job)
        loc_score = self._location_match(city)

        # 加权
        weighted = (
            skill_score * 0.4
            + exp_score * 0.3
            + hard_score * 0.2
            + loc_score * 0.1
        )

        reasons = []
        if skill_score >= 60:
            reasons.append(f"技能匹配度{skill_score}%")
        if exp_score >= 50:
            reasons.append(f"经验相关度{exp_score}%")
        if loc_score >= 70:
            reasons.append(f"目标城市{loc_score}%")

        gaps = []
        if skill_score < 50:
            gaps.append("部分技能不完全匹配，可在简历中强化相关项目经验")
        if exp_score < 40:
            gaps.append("行业经验偏少，建议突出可迁移的数据处理能力")

        return {
            "match_score": int(weighted),
            "reasons": reasons[:3],
            "gaps": gaps[:2],
            "suggestions": (
                "推荐投递" if weighted >= 70 else
                "可以投递" if weighted >= 50 else
                "谨慎投递" if weighted >= 30 else
                "不太匹配"
            ),
        }

    def evaluate(self, job: dict) -> dict:
        """A-G 评估（模拟 AI evaluate_job 输出）"""
        title = (job.get("title") or "")
        desc = (job.get("description") or "")
        company = (job.get("company") or "")
        city = (job.get("city") or "")

        # 原型分类
        arch = detect_archetype(desc, title)

        # 匹配
        m = self.match(job)
        score = self._to_5star(m["match_score"])

        # 薪资评估
        salary_min = job.get("salary_min", 0) or 0
        comp = self._comp_eval(city, salary_min)

        # 合法性
        legit = self._legitimacy_check(title, desc, company)

        return {
            "A_role_summary": {
                "archetype": arch["label"],
                "domain": self._guess_domain(title),
                "function": self._guess_function(title),
                "seniority": self._guess_level(title),
                "tldr": self._one_line(title, company),
            },
            "B_cv_match": {
                "skills_match": m["match_score"],
                "experience_match": self._experience_match(title, desc, company),
                "hard_match": self._hard_match(job),
                "location_match": self._location_match(city),
                "gaps": [f"关键词匹配评估，非AI精确分析"],
            },
            "C_level_strategy": {
                "jd_level": self._guess_level(title),
                "candidate_level": "硕士·应届/1-3年",
                "sell_up": "强调AI+环境交叉背景" if arch["confidence"] > 0.3 else "强调Python技术能力",
                "if_downlevel": "硕士起点不应接受低于5K的薪资",
            },
            "D_comp": {
                "market_range": comp["range"],
                "jd_vs_market": comp["vs_market"],
                "note": comp["note"],
            },
            "E_resume_custom": {
                "changes": self._resume_tips(title, desc, arch),
            },
            "F_interview": {
                "questions": self._interview_questions(title, arch),
                "ask_hr": ["团队目前的技术栈是什么?", "入职后会接触哪些项目?"],
                "star_story": {
                    "situation": "PM2.5时空数据融合研究",
                    "task": "融合卫星遥感+地面监测多源数据",
                    "action": "用Python实现时空插值和数据融合算法",
                    "result": "生成高精度PM2.5浓度分布图",
                    "reflection": "理解了多源数据融合的核心挑战",
                },
                "salary_tip": "结合城市薪资水平，硕士应届6-12K合理",
            },
            "G_legitimacy": legit,
            "overall_score": score,
            "apply_recommendation": (
                "推荐投递" if score >= 4.0 else
                "可以投递" if score >= 3.5 else
                "谨慎" if score >= 2.5 else
                "不建议"
            ),
            "red_flags": [],
        }

    # ─── 私有方法 ──────────────────────────────────────

    def _skill_match(self, title: str, desc: str, company: str) -> int:
        """技能匹配：标题权重 > 描述权重"""
        text = f"{title} {desc} {company}"
        hits = sum(1 for s in self.skills if s in text)
        # 基础分 = 命中数/期望命中数 * 100，至少保底 20
        base = int(hits / max(len(self.skills) * 0.2, 1) * 100)
        return min(max(base, 20), 100)

    def _experience_match(self, title: str, desc: str, company: str) -> int:
        text = f"{title} {desc} {company}"
        hits = sum(1 for e in self.experience if e in text)
        base = int(hits / max(len(self.experience) * 0.2, 1) * 100)
        return min(max(base, 15), 100)

    def _hard_match(self, job: dict) -> int:
        score = 100
        edu = (job.get("education") or "").lower()
        if edu and "博士" in edu:
            score -= 30  # 博士岗不投
        if edu and ("硕士" in edu or "研究生" in edu):
            score += 10
        exp = (job.get("experience") or "")
        if re.search(r"5[年]|八年|十年", exp):
            score -= 20  # 要求经验太高
        return max(score, 0)

    def _location_match(self, city: str) -> int:
        if not city:
            return 50
        city_l = city.lower()
        for c in self.target_cities:
            if c in city_l:
                if c in ("南宁", "广州", "深圳"):
                    return 100
                return 85
        return 30

    def _comp_eval(self, city: str, salary_min: int) -> dict:
        city_k = city or "default"
        lo, hi = MARKET_SALARY.get(city_k, MARKET_SALARY["default"])
        rng = f"{lo//1000}K-{hi//1000}K"
        if salary_min == 0:
            return {"range": rng, "vs_market": "面议", "note": "面议需面试谈"}
        if salary_min >= hi:
            return {"range": rng, "vs_market": "偏高", "note": "薪资有竞争力"}
        if salary_min < lo * 0.7:
            return {"range": rng, "vs_market": "偏低", "note": "低于市场水平"}
        return {"range": rng, "vs_market": "中等", "note": "符合市场水平"}

    def _legitimacy_check(self, title: str, desc: str, company: str) -> dict:
        signals = []
        confidence = "中"
        if len(desc or "") < 50:
            signals.append("岗位描述过于简短")
            confidence = "低"
        if "常年招聘" in title or "大量招人" in title:
            signals.append("疑似常年招聘")
            confidence = "低"
        if "培训" in title and "学徒" in title:
            signals.append("疑似培训招生")
            confidence = "低"
        if company and len(company) < 3:
            signals.append("公司名过短")
            confidence = "低"
        if not signals:
            signals.append("初步检查无明显风险信号")
        return {
            "is_real": confidence != "低",
            "confidence": confidence,
            "signals": signals,
            "verdict": "真实" if confidence != "低" else "可疑",
        }

    def _guess_domain(self, title: str) -> str:
        if any(w in title for w in ["大气", "空气质量", "PM", "气象"]):
            return "大气环境"
        if any(w in title for w in ["水", "水务", "废水"]):
            return "水环境"
        if any(w in title for w in ["遥感", "GIS", "地理"]):
            return "遥感/GIS"
        return "环境通用"

    def _guess_function(self, title: str) -> str:
        if any(w in title for w in ["开发", "工程师", "全栈", "软件"]):
            return "开发"
        if any(w in title for w in ["数据", "分析", "AI", "算法", "模型"]):
            return "数据分析"
        if any(w in title for w in ["环评", "咨询"]):
            return "咨询"
        if any(w in title for w in ["监测", "检测"]):
            return "监测"
        return "技术"

    def _guess_level(self, title: str) -> str:
        if any(w in title for w in ["高级", "资深", "技术总监", "首席"]):
            return "高级"
        if any(w in title for w in ["实习", "管培"]):
            return "初级"
        return "中级"

    def _one_line(self, title: str, company: str) -> str:
        return f"{company}招聘{title[:15]}"

    def _to_5star(self, pct: int) -> float:
        """将 0-100 百分比映射到 0-5 分制，保证合理的最低分"""
        if pct <= 0:
            return 2.0  # 无信息也至少给2分
        if pct <= 10:
            return 2.0
        if pct <= 20:
            return 2.5
        if pct <= 30:
            return 3.0
        if pct <= 40:
            return 3.5
        if pct <= 60:
            return 4.0
        if pct <= 80:
            return 4.5
        return 5.0

    def _resume_tips(self, title: str, desc: str, arch: dict) -> list:
        tips = ["在简历摘要中突出AI+环境交叉背景"]
        if arch.get("archetype") == "env_tech":
            tips.append("强调你是'会用AI做环境数据分析'的硕士,而不是传统的环评/监测方向")
        if "python" in title.lower():
            tips.append("项目经验部分用Python技术栈重新组织,把爬虫/自动化/AI案例放最前面")
        if "数据" in title or "分析" in title:
            tips.append("突出PM2.5数据融合研究中的数据处理和分析能力")
        if "遥感" in title or "GIS" in title:
            tips.append("强调卫星遥感+地面监测多源数据融合经验")
        return tips[:5] + ["简历语言用STAR法则重写项目经历"]

    def _interview_questions(self, title: str, arch: dict) -> list:
        qs = [
            {"q": "请介绍一下你的PM2.5数据融合研究", "hint": "用STAR法则,突出技术栈和成果"},
            {"q": "你如何用Python/AI解决环境领域的问题?", "hint": "举AI求职系统/browser-act等实际案例"},
        ]
        if arch.get("archetype") == "env_tech":
            qs.append({"q": "为什么选择环境+计算机交叉方向?", "hint": "回答行业数字化转型趋势+你的独特优势"})
        else:
            qs.append({"q": "你对我们公司/这个岗位了解多少?", "hint": "提前研究公司业务+岗位需求"})
        return qs + [{"q": "未来3-5年的职业规划?", "hint": "环境数字化领域深耕"}]


def quick_match(job: dict, skills: list = None) -> dict:
    """快速匹配（一行调用）"""
    return KeywordMatcher(skills=skills).match(job)


def quick_eval(job: dict) -> dict:
    """快速评估（一行调用）"""
    return KeywordMatcher().evaluate(job)
