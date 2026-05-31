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
        self.provider = config.get("ai", "provider", "openai")
        self.model = config.get("ai", "model", "gpt-4o-mini")
        self.api_key = config.get("ai", "api_key", "")
        self.api_base = config.get("ai", "api_base", "")

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

    # ─── 岗位评估 ─────────────────────────────────────────

    def evaluate_job(self, job: dict, resume: dict) -> dict:
        """LLM六维评估岗位（参考Career-Ops体系）"""
        system = """你是专业的职业评估师。请从6个维度深度评估岗位。
返回JSON：
{
  "岗位匹配度": {"score": "A+/A/A-/B+/B/B-/C/D/F", "comment": "20字以内"},
  "职级定位": {"score": "A+/A/A-/B+/B/B-/C/D/F", "comment": "20字以内"},
  "薪资水平": {"score": "A+/A/A-/B+/B/B-/C/D/F", "comment": "20字以内"},
  "公司质量": {"score": "A+/A/A-/B+/B/B-/C/D/F", "comment": "20字以内"},
  "成长空间": {"score": "A+/A/A-/B+/B/B-/C/D/F", "comment": "20字以内"},
  "投递优先级": "★★★★★（1-5星）",
  "overall_score": "A/A-/B+/B/C（综合评级）",
  "interview_questions": ["面试可能问题1", "问题2"],
  "advice": "准备建议（60字以内）"
}"""
        job_text = json.dumps(job, ensure_ascii=False)
        resume_text = json.dumps(resume, ensure_ascii=False)
        result = self._call_llm(
            system,
            f"求职者：{resume_text}\n岗位：{job_text}",
            temperature=0.3, max_tokens=1500,
        )
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
            return {}

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
