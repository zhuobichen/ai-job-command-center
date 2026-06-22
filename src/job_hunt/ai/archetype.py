"""
岗位原型分类（Archetype Detection）
====================================
参考 career-ops 的理念，根据 JD 文字将岗位归入原型，
不同原型采用不同的评估策略和简历优化方案。
"""

# 岗位原型定义
ARCHETYPES = {
    "python_dev": {
        "label": "Python 开发",
        "keywords": ["Python", "Django", "Flask", "FastAPI", "后端", "开发工程师",
                     "软件工程师", "Web开发", "API", "自动化脚本"],
        "strategy": "强调项目经验、自动化脚本能力、全栈潜力",
        "proof_point_priority": ["项目经验", "技术栈熟练度", "自动化工具链"],
    },
    "data_analysis": {
        "label": "数据分析",
        "keywords": ["数据分析", "数据处理", "pandas", "numpy", "BI", "报表",
                     "数据挖掘", "SQL", "Excel", "可视化", "统计"],
        "strategy": "强调数据处理能力、PM2.5数据融合经验、学术严谨性",
        "proof_point_priority": ["数据分析项目", "学术数据处理", "报告撰写"],
    },
    "ai_informatization": {
        "label": "AI/信息化",
        "keywords": ["人工智能", "AI", "机器学习", "深度学习", "大模型", "LLM",
                     "信息化", "数字化转型", "智能", "Agent", "ChatGPT",
                     "自然语言处理", "计算机视觉", "算法"],
        "strategy": "强调LLM应用经验、AI工具链掌握、自动化创新能力",
        "proof_point_priority": ["AI项目经验", "自动化成果", "学习能力"],
    },
    "env_tech": {
        "label": "环境科技",
        "keywords": ["环境", "环保", "大气", "监测", "PM2.5", "AQI",
                     "生态", "环评", "排污", "碳", "排放", "污染",
                     "水利", "水务", "气象"],
        "strategy": "强调专业对口+技术赋能，环境背景是优势不是限制",
        "proof_point_priority": ["专业背景", "技术应用", "数据融合经验"],
    },
    "government": {
        "label": "政府事业",
        "keywords": ["事业编", "事业单位", "公务员", "国企", "编制",
                     "机关", "局", "管委会", "党政", "高新区", "经开区"],
        "strategy": "强调学历、稳定性、专业匹配、服务意识",
        "proof_point_priority": ["学历背景", "专业对口", "稳定性"],
    },
}


def detect_archetype(job_description: str = "", job_title: str = "") -> dict:
    """根据岗位文字检测所属原型

    Args:
        job_description: 岗位描述
        job_title: 岗位标题

    Returns:
        {
            "archetype": "python_dev",  # 主原型 ID
            "label": "Python 开发",       # 中文名
            "confidence": 0.8,            # 置信度 0-1
            "hybrid": "data_analysis",    # 次原型（如有）
            "strategy": "...",
            "matched_keywords": ["Python", "Django"],
        }
    """
    text = (job_title + " " + (job_description or "")).lower()
    scores = {}

    for arch_id, arch in ARCHETYPES.items():
        score = 0
        matched = []
        for kw in arch["keywords"]:
            if kw.lower() in text:
                # 关键词越长权重越高
                weight = min(len(kw), 6) / 6
                score += weight
                matched.append(kw)
        if matched:
            if "开发" in text or "代码" in text or "编程" in text:
                score += 0.5
            scores[arch_id] = score

    if not scores:
        return {
            "archetype": "python_dev",
            "label": "Python 开发",
            "confidence": 0.1,
            "strategy": "默认原型（无匹配关键词）",
            "matched_keywords": [],
        }

    # 按得分降序
    sorted_archs = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary_id, primary_score = sorted_archs[0]

    # 归一化
    max_possible = len(ARCHETYPES[primary_id]["keywords"])
    confidence = min(primary_score / max(max_possible / 2, 1), 1.0)

    result = {
        "archetype": primary_id,
        "label": ARCHETYPES[primary_id]["label"],
        "confidence": round(confidence, 2),
        "strategy": ARCHETYPES[primary_id]["strategy"],
    }

    # 次原型（得分 > 主原型 60% 的）
    if len(sorted_archs) > 1:
        secondary_id, secondary_score = sorted_archs[1]
        if secondary_score > primary_score * 0.6:
            result["hybrid"] = secondary_id
            result["hybrid_label"] = ARCHETYPES[secondary_id]["label"]

    # 记录匹配关键词
    text_lower = text
    matched = []
    for kw in ARCHETYPES[primary_id]["keywords"]:
        if kw.lower() in text_lower:
            matched.append(kw)
    result["matched_keywords"] = matched[:10]

    return result


def get_proof_point_priority(archetype_id: str) -> list:
    """获取某原型的证明点优先级"""
    arch = ARCHETYPES.get(archetype_id)
    return arch["proof_point_priority"] if arch else []
