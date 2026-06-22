"""AI 编排层 - LLM 交互、意图识别、任务分发"""

import json
from typing import Optional

from ..utils.config import Config
from ..utils.display import print_ai, print_info


# 懒加载 litellm，避免安装前阻塞CLI
def _get_completion():
    try:
        from litellm import completion
        return completion
    except ImportError:
        raise ImportError(
            "litellm 未安装，请运行: pip install litellm"
        )


class AIBrain:
    """AI核心大脑 - 封装所有LLM调用"""

    def __init__(self, config: Config):
        self.config = config
        self.provider = config.get("ai", "provider", "deepseek")
        self.model = config.get("ai", "model", "deepseek-chat")
        # API key: 配置文件优先，其次 DEEPSEEK_API_KEY 环境变量（与 weflow-cli 一致）
        self.api_key = config.get_api_key()
        self.api_base = config.get("ai", "api_base", "") or "https://api.deepseek.com"

    def _call_llm(self, system: str, user: str, temperature: float = 0.7, 
                  max_tokens: int = 2000, response_format: Optional[dict] = None) -> str:
        """通用LLM调用"""
        kwargs = dict(
            model=f"{self.provider}/{self.model}",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=self.api_key,
        )
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if response_format:
            kwargs["response_format"] = response_format

        print_ai("AI思考中...")
        completion = _get_completion()
        resp = completion(**kwargs)
        content = resp.choices[0].message.content
        return content.strip()

    # ─── 简历解析 ─────────────────────────────────────────

    def parse_resume(self, raw_text: str) -> dict:
        """LLM提取简历结构化信息"""
        system = """你是一位专业的简历解析专家。请从简历文本中提取结构化信息。
返回严格的JSON格式，所有字段存在但可为空字符串或0：
{
  "name": "姓名",
  "phone": "手机号",
  "email": "邮箱",
  "wechat": "微信号（如有）",
  "education_level": "本科/硕士/博士",
  "university": "学校全称",
  "major": "专业全称",
  "graduation_year": 2024,
  "projects": "项目经验的JSON数组字符串，每个项目含name/description/role/tech",
  "skills": "技术栈逗号分隔",
  "work_years": 工作年限数字,
  "desired_city": "意向城市（从简历中推断或留空）",
  "desired_position": "意向职位（从简历中推断或留空）",
  "salary_min": 期望最低月薪数字,
  "salary_max": 期望最高月薪数字
}"""
        result = self._call_llm(system, f"简历内容：\n{raw_text[:5000]}", 
                                temperature=0.1, max_tokens=2000)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # 尝试提取JSON
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
            return {}

    # ─── 岗位匹配 ─────────────────────────────────────────

    def match_job(self, resume: dict, job: dict) -> dict:
        """LLM评估岗位与简历的匹配度"""
        system = """你是专业的求职匹配评估师。请评估求职者与岗位的匹配度。
返回JSON：
{
  "match_score": 0-100的数字,
  "reasons": ["匹配点1", "匹配点2"],
  "gaps": ["差距点1"],
  "suggestions": "投递建议（40字以内）"
}

评估维度权重：
- 技能匹配 40%：技术栈、工具、方法的匹配
- 经验匹配 30%：行业背景、项目类型的匹配
- 硬性匹配 20%：学历、工作年限、专业要求
- 地点/薪资 10%：城市一致性、薪资范围匹配"""

        resume_text = json.dumps(resume, ensure_ascii=False)
        job_text = json.dumps({
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "city": job.get("city", ""),
            "salary": job.get("salary_text", ""),
            "education": job.get("education", ""),
            "experience": job.get("experience", ""),
            "description": (job.get("description", "") or "")[:1000],
            "requirements": (job.get("requirements", "") or "")[:500],
            "tags": job.get("tags", ""),
        }, ensure_ascii=False)

        result = self._call_llm(
            system,
            f"求职者简历：\n{resume_text}\n\n岗位信息：\n{job_text}",
            temperature=0.3, max_tokens=1000,
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
            return {"match_score": 0, "reasons": [], "gaps": []}

    # ─── 岗位评估（A-G 八块体系）─────────────────────────

    def evaluate_job(self, job: dict, resume: dict) -> dict:
        """LLM八块评估岗位（A-G体系，参考Career-Ops）

        A: 角色摘要 — 原型分类+领域+职能+级别
        B: 简历匹配 — JD要求逐条对照简历
        C: 级别策略 — JD要求的级别 vs 你的真实级别
        D: 薪酬调研 — 市场薪资区间对比
        E: 简历定制 — 5点定制化改动
        F: 面试准备 — STAR+R故事
        G: 合法性检查 — 岗位真实性
        """
        system = """你是专业的职业咨询师。请用A-G八块体系深度评估岗位。

## 评估体系

### A. 角色摘要
判断岗位原型（Python开发/数据分析/AI信息化/环境科技/政府事业），提取：领域、职能（开发/分析/管理/部署）、级别（初级/中级/高级/专家）、远程模式。

### B. 简历匹配
逐条对照JD要求→简历是否有对应行：
- 技能匹配（40%权重）：技术栈、工具的匹配度
- 经验匹配（30%权重）：行业背景、项目类型
- 硬性匹配（20%权重）：学历、年限、专业
- 地点/薪资（10%权重）
每项缺失要有弥补方案：是否是硬性门槛？能否用邻近经验证明？有没有可快速补齐的？

### C. 级别策略
JD要求的级别 vs 求职者当前级别：
- 如果JD要求偏高：如何"卖资历"（用具体项目成果体现高级别能力）
- 如果JD要求偏低：是否接受降级（薪资是否匹配，6个月晋升评估条款）

### D. 薪酬市场调研
基于你对该岗位/城市/级别的了解：
- 该岗在广西/广东的市场薪资区间
- JD薪资与市场的对比（高/中/低）
- 如果薪资面议，给出预期范围建议

### E. 简历定制化方案
5点具体的简历改动建议（按优先级）：
- 哪段经历要重写（用STAR法则）
- 哪个技能要高亮（JD要求的）
- 哪个项目要放到最前面
- 摘要怎么改写
- LinkedIn/在线简历怎么同步

### F. 面试准备
- 3-5个大概率被问到的问题（含回答思路）
- 2-3个建议反问HR的问题
- 1个STAR故事（情境-任务-行动-结果-反思）
- 薪资谈判建议（30字）

### G. 岗位真实性检查
基于以下信号判断岗位是否真实有效：
- JD中技术描述的详细程度（越具体越真）
- 薪资与市场匹配度（异常高/低）
- 公司是否有明确的业务描述
- 是否有"常年招聘""大量招人"等危险信号

## 评分标准
- overall_score: 1.0-5.0（加权平均，4.0+可投，3.5-3.9谨慎，<3.5不建议）
- apply_recommendation: "强烈推荐"/"推荐"/"可以投"/"谨慎"/"不建议"
- 如果有红线（如薪资严重偏低、岗位疑似虚假），在red_flags中列出

## 输出格式
返回严格JSON（不要markdown代码块标记）：
{
  "A_role_summary": {"archetype": "原型", "domain": "领域", "function": "职能", "seniority": "级别", "tldr": "一句话摘要15字"},
  "B_cv_match": {"skills_match": 0-100, "experience_match": 0-100, "hard_match": 0-100, "location_match": 0-100, "gaps": ["缺失1 弥补方案", "缺失2 弥补方案"]},
  "C_level_strategy": {"jd_level": "级别", "candidate_level": "级别", "sell_up": "如何卖资历", "if_downlevel": "降级策略"},
  "D_comp": {"market_range": "区间", "jd_vs_market": "高/中/低", "note": "薪酬说明20字"},
  "E_resume_custom": {"changes": ["改动1", "改动2", "改动3", "改动4", "改动5"]},
  "F_interview": {"questions": [{"q": "问题", "hint": "回答思路"}], "ask_hr": ["反问1", "反问2"], "star_story": {"situation": "", "task": "", "action": "", "result": "", "reflection": ""}, "salary_tip": "谈判建议"},
  "G_legitimacy": {"is_real": true/false, "confidence": "高/中/低", "signals": ["信号1"], "verdict": "真实/可疑/虚假"},
  "overall_score": 4.2, "apply_recommendation": "推荐", "red_flags": []
}"""
        job_text = json.dumps(job, ensure_ascii=False)
        resume_text = json.dumps(resume, ensure_ascii=False)
        result = self._call_llm(
            system,
            f"## 求职者简历\n{resume_text}\n\n## 目标岗位\n{job_text}",
            temperature=0.3, max_tokens=2500,
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(result[start:end])
                except json.JSONDecodeError:
                    pass
            return {
                "overall_score": 0,
                "apply_recommendation": "无法评估",
                "A_role_summary": None,
                "B_cv_match": None,
                "C_level_strategy": None,
                "D_comp": None,
                "E_resume_custom": None,
                "F_interview": None,
                "G_legitimacy": None,
                "red_flags": ["AI评估解析失败"],
            }

    # ─── 简历生成 ─────────────────────────────────────────

    def generate_resume(self, resume: dict, job: dict) -> str:
        """LLM根据JD优化简历"""
        system = """你是专业的简历优化师。请根据岗位JD定制化优化求职者的简历。
要求：
1. 保留简历中的事实信息，不要编造经历
2. 针对JD中的关键词，用求职者的真实经历去匹配
3. 重新排序项目经历，最匹配的放最前面
4. 工作经历描述用STAR法则（情境-任务-行动-结果）
5. 技能部分高亮JD要求的技能
6. 输出格式为Markdown，包含以下章节：
   - # 个人信息
   - # 求职意向
   - # 教育背景
   - # 技能概览
   - # 项目经历
   - # 工作经历
   - # 荣誉奖项
"""
        job_text = json.dumps(job, ensure_ascii=False)
        resume_text = json.dumps(resume, ensure_ascii=False)
        return self._call_llm(
            system,
            f"原始简历：\n{resume_text}\n\n目标岗位JD：\n{job_text}",
            temperature=0.5, max_tokens=3000,
        )

    # ─── 对话模式 ─────────────────────────────────────────

    def chat(self, user_message: str, context: dict) -> str:
        """对话模式 - 自由问答"""
        system = f"""你是AI求职助手，帮助用户在中国找工作的智能助手。
用户信息：{json.dumps(context.get('resume', {}), ensure_ascii=False)}
当前岗位库有 {context.get('job_count', 0)} 个待分析岗位。
你的能力包括：搜索岗位、评估匹配度、优化简历、准备面试、分析薪资。

请用中文简洁回答，像朋友一样，给出可操作的建议。"""
        return self._call_llm(system, user_message, temperature=0.7, max_tokens=2000)

    # ─── 打招呼语 ─────────────────────────────────────────

    def generate_greeting(self, resume: dict, job: dict) -> str:
        """生成个性化打招呼语"""
        system = """你是求职沟通专家。请生成一句简短的打招呼语（30字以内），
中文，用于BOSS直聘等招聘平台初次联系HR。
要求：提到1-2个与岗位匹配的关键技能，语气专业但友好。"""
        return self._call_llm(
            system,
            f"求职者：{json.dumps(resume, ensure_ascii=False)[:300]}\n岗位：{json.dumps(job, ensure_ascii=False)[:300]}",
            temperature=0.7, max_tokens=100,
        )

    # ─── 面试准备 ─────────────────────────────────────────

    def prepare_interview(self, job: dict, resume: dict) -> dict:
        """生成面试准备材料"""
        system = """你是面试辅导专家。请根据岗位JD和求职者背景，生成面试准备材料。
返回JSON：
{
  "key_points": ["面试核心要讲的3个要点"],
  "questions": ["可能被问到的问题列表（5个）"],
  "answers_hints": ["回答思路提示"],
  "questions_to_ask": ["建议反问HR的问题（3个）"],
  "salary_tips": "薪资谈判建议（40字以内）"
}"""
        result = self._call_llm(
            system,
            f"岗位：{json.dumps(job, ensure_ascii=False)}\n求职者：{json.dumps(resume, ensure_ascii=False)}",
            temperature=0.5, max_tokens=1500,
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
            return {}
