"""公司信息交叉验证模块

验证流程：
  第一层：工商注册信息（天眼查/企查查/国家企业信用信息公示系统）
  第二层：官方渠道确认（企业官网、主管单位官网）
  第三层：招聘真实性（官方招聘公告 vs 第三方转载）
  第四层：部门/业务真实性（组织架构、实际业务范围）
  第五层：风险扫描（失信、被执行、行政处罚、劳动纠纷）
"""

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VerifyResult:
    """验证结果"""
    company_name: str = ""

    # 第一层：工商注册
    registered: bool = False            # 是否合法注册
    registration_info: str = ""        # 注册信息摘要

    # 第二层：官方渠道
    has_website: bool = False          # 是否有官网
    website_url: str = ""              # 官网地址
    is_state_owned: str = ""           # 企业性质：国企/事业/民企/外企

    # 第三层：招聘真实性
    has_recent_hiring: bool = False    # 近期是否有招聘
    hiring_sources: str = ""           # 招聘渠道列表
    hiring_confirmed: bool = False     # 招聘信息是否官方确认

    # 第四层：业务真实性
    business_lines: str = ""           # 实际业务范围
    has_target_dept: bool = False      # 是否有目标方向相关部门

    # 第五层：风险扫描
    risk_level: str = ""               # 绿色/黄色/红色
    risk_details: str = ""             # 风险详情

    # 综合
    overall_score: int = 0             # 综合可信度 0-100
    verdict: str = ""                  # 可信/待确认/存疑/排除
    evidence: str = ""                 # 证据摘要
    warnings: list = field(default_factory=list)  # 警告列表

    @property
    def verdict_display(self) -> str:
        mapping = {
            "可信": "🟢 可信",
            "待确认": "🟡 待确认",
            "存疑": "🔴 存疑",
            "排除": "⚫ 排除",
        }
        return mapping.get(self.verdict, self.verdict)


def _get_completion():
    try:
        from litellm import completion
        return completion
    except ImportError:
        raise ImportError("litellm 未安装")


# ─── 验证 Prompt 模板 ────────────────────────────────────

VERIFY_SYSTEM_PROMPT = """你是企业信息核查专家。请严格基于提供的搜索结果进行交叉验证，不得编造任何信息。

## 验证规则

### 第一层：工商注册
- ✅ 可信信号：国家企业信用信息公示系统、天眼查、企查查中有明确记录
- ❌ 危险信号：搜索不到任何工商信息 / 多个搜索结果互相矛盾

### 第二层：官方渠道
- ✅ 可信信号：有独立官网域名 / 作为事业单位在主管厅局官网有独立页面
- ❌ 危险信号：官网打不开 / 官网内容与搜索到的招聘信息矛盾

### 第三层：招聘真实性
- ✅ 可信信号：招聘公告出现在官网/广西人才网/主管厅局人事栏目 / 事业单位统考公告
- ❌ 危险信号：仅在非官方平台（贴吧/微信群/个人公众号）出现 / 薪资远超行业水平

### 第四层：部门/业务真实性
- ✅ 可信信号：招聘公告中明确写了相关部门和职责
- ⚠️ 待确认：搜索结果中未提及该部门/业务，但也不能排除

### 第五层：风险扫描
- 🔴 高风险排除：有失信/被执行/吊销营业执照/大量劳动仲裁
- 🟡 中风险待确认：有行政处罚但已处理 / 成立不满1年
- 🟢 低风险：无任何风险记录

## 评分标准
- 90-100：五层全部通过 ✅
- 70-89：前四层通过，第五层有轻微瑕疵
- 50-69：有一层重要信息无法确认
- 30-49：有两层以上无法确认或存在矛盾
- 0-29：存在严重风险信号，建议排除

## 输出格式
返回严格的JSON，不要有额外文字：
{
  "company_name": "公司全称",
  "registered": true/false,
  "registration_info": "工商信息摘要（成立日期、注册资本、法人代表等，30字以内）",
  "has_website": true/false,
  "website_url": "官网地址或空",
  "is_state_owned": "事业单位/国有企业/民营企业/外资企业/未知",
  "has_recent_hiring": true/false,
  "hiring_sources": "招聘渠道列表（广西人才网/官网/区直统考/BOSS直聘等）",
  "hiring_confirmed": true/false,
  "business_lines": "主营业务方向（20字以内）",
  "has_target_dept": true/false,
  "risk_level": "绿色/黄色/红色",
  "risk_details": "风险说明（如无风险写'未发现'）",
  "overall_score": 0-100,
  "verdict": "可信/待确认/存疑/排除",
  "evidence": "关键证据摘要（40字以内，说明为什么给出这个结论）",
  "warnings": ["具体的警告信息，如无警告则为空数组"]
}

## 特别注意
- SEARCH RESULTS 中如果没有提到某个信息，就标注为 unknown，不要编造
- 如果多个来源信息互相矛盾，必须在 evidence 中说明
- 宁可不确认，不可误判为可信"""


def parse_verify_result(raw: str, company_name: str) -> VerifyResult:
    """解析 LLM 返回的 JSON 验证结果"""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start:end])
            except json.JSONDecodeError:
                # LLM 返回异常时，返回存疑结果
                return VerifyResult(
                    company_name=company_name,
                    verdict="存疑",
                    overall_score=0,
                    evidence="AI 解析失败，请手动验证",
                    warnings=["无法自动完成验证，建议手动查询天眼查"],
                )
        else:
            return VerifyResult(
                company_name=company_name,
                verdict="存疑",
                overall_score=0,
                evidence="AI 解析失败，请手动验证",
                warnings=["无法自动完成验证，建议手动查询天眼查"],
            )

    return VerifyResult(
        company_name=data.get("company_name", company_name),
        registered=data.get("registered", False),
        registration_info=data.get("registration_info", ""),
        has_website=data.get("has_website", False),
        website_url=data.get("website_url", ""),
        is_state_owned=data.get("is_state_owned", ""),
        has_recent_hiring=data.get("has_recent_hiring", False),
        hiring_sources=data.get("hiring_sources", ""),
        hiring_confirmed=data.get("hiring_confirmed", False),
        business_lines=data.get("business_lines", ""),
        has_target_dept=data.get("has_target_dept", False),
        risk_level=data.get("risk_level", "黄色"),
        risk_details=data.get("risk_details", ""),
        overall_score=data.get("overall_score", 0),
        verdict=data.get("verdict", "待确认"),
        evidence=data.get("evidence", ""),
        warnings=data.get("warnings", []),
    )


def verify_company(company_name: str, target_direction: str = "") -> VerifyResult:
    """对一家公司进行五层交叉验证

    Args:
        company_name: 公司全称
        target_direction: 目标方向（如"环境信息系统"），用于判断是否有对口部门
    """
    completion = _get_completion()

    # ─── 构建搜索结果摘要 ────────────────────────────────
    search_summary_parts = []

    # 模拟多源搜索的说明
    # 注意：实际搜索由外部完成，这里只做 LLM 汇总判断
    # 在 CLI 命令中会先进行 WebSearch，再把结果传进来

    prompt = f"""请对以下公司进行五层交叉验证：

## 目标公司
公司全称：{company_name}
关注方向：{target_direction or "无特定方向"}

## 操作说明
当前模式为快速验证。请基于你对公开信息的了解给出初步判断。
对于事业单位和大型国企，你有较高置信度的了解。
对于小型民企，你应当给出保守的"待确认"结论并建议用户手动查天眼查。

## 输出
返回JSON格式的验证结果，遵循验证规则。

注意：
- 如果公司是知名事业单位/国企，可以给出较高置信度
- 如果是你不太了解的小型民企，给30-50分并标注"待确认"
- 绝对不能编造注册号、具体注册资本等需要精确查询的信息
- 如果有不确定的信息，在对应的字段留空或标注为false"""

    resp = completion(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "system", "content": VERIFY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2000,
        temperature=0.1,  # 低温度，减少幻觉
        api_key=_get_api_key(),
    )

    content = resp.choices[0].message.content
    return parse_verify_result(content.strip(), company_name)


def verify_company_with_search(
    company_name: str,
    search_results: str,
    target_direction: str = "",
) -> VerifyResult:
    """基于实际搜索结果进行交叉验证（更准确）"""
    completion = _get_completion()

    prompt = f"""请基于以下实际搜索结果，对目标公司进行五层交叉验证。

## 目标公司
公司全称：{company_name}
关注方向：{target_direction or "无特定方向"}

## 搜索结果
{search_results}

## 要求
1. 严格基于搜索结果做出判断
2. 搜索结果中没有提及的信息，标注为 false 或留空
3. 如果搜索结果相互矛盾，在 evidence 中说明矛盾点
4. 输出严格的 JSON 格式"""

    resp = completion(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "system", "content": VERIFY_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=2000,
        temperature=0.1,
        api_key=_get_api_key(),
    )

    content = resp.choices[0].message.content
    return parse_verify_result(content.strip(), company_name)


def _get_api_key() -> str:
    """从配置文件读取 API Key"""
    try:
        from ..utils.config import Config
        c = Config()
        return c.ai.get("api_key", "")
    except Exception:
        import os
        # 尝试从环境变量获取
        return os.environ.get("DEEPSEEK_API_KEY", "")
