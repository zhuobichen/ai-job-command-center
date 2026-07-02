"""多平台搜索模板与站点配置"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class SearchSite:
    """搜索站点配置"""
    name: str            # 站点名称
    site_domain: str     # 域名（用于 site: 限定）
    priority: int        # 优先级 1-5
    weight: float        # 分配权重（总共1.0）
    category: str        # 分类：综合招聘/地方平台/事业单位/垂直行业
    search_url_template: str = ""   # 直接搜索URL模板
    notes: str = ""      # 备注
    
    @property
    def is_local(self) -> bool:
        """是否广西本地渠道"""
        return self.category in ("地方平台", "事业单位")


# ─── 广西求职核心渠道 ─────────────────────────────────────

GUANGXI_SITES: List[SearchSite] = [
    # 🔴 第一优先级：广西本地主渠道
    SearchSite(
        name="广西人才网",
        site_domain="gxrc.com",
        priority=1,
        weight=0.20,
        category="地方平台",
        search_url_template="https://www.gxrc.com/job/search?keyword={keyword}",
        notes="广西最大官方招聘平台，事业单位/国企主渠道",
    ),
    SearchSite(
        name="广西生态环境厅",
        site_domain="sthjt.gxzf.gov.cn",
        priority=1,
        weight=0.12,
        category="事业单位",
        notes="直属事业单位招聘公告发布处（环科院/监测中心等）",
    ),
    SearchSite(
        name="广西人才市场",
        site_domain="gxrcda.com",
        priority=1,
        weight=0.08,
        category="地方平台",
        notes="广西人才市场官方网站",
    ),
    
    # 🟡 第二优先级：全国招聘 + 广西定位
    SearchSite(
        name="BOSS直聘",
        site_domain="zhipin.com",
        priority=2,
        weight=0.15,
        category="综合招聘",
        notes="岗位量最大，但反爬严格，用搜索引擎间接抓",
    ),
    SearchSite(
        name="前程无忧",
        site_domain="51job.com",
        priority=2,
        weight=0.12,
        category="综合招聘",
        notes="传统招聘巨头，国企岗位较多",
    ),
    SearchSite(
        name="智联招聘",
        site_domain="zhaopin.com",
        priority=2,
        weight=0.08,
        category="综合招聘",
        notes="覆盖面广，适合环保类岗位",
    ),
    
    # 🟢 第三优先级：补充渠道
    SearchSite(
        name="猎聘",
        site_domain="liepin.com",
        priority=3,
        weight=0.08,
        category="综合招聘",
        notes="中高端岗位",
    ),
    SearchSite(
        name="桂聘网",
        site_domain="guipin.com",
        priority=3,
        weight=0.05,
        category="地方平台",
        notes="广西本地招聘平台",
    ),
    SearchSite(
        name="广西各地市人社局",
        site_domain="gov.cn",
        priority=3,
        weight=0.05,
        category="事业单位",
        notes="各地市人力资源和社会保障局招聘公告",
    ),
    SearchSite(
        name="高校就业网",
        site_domain="edu.cn",
        priority=3,
        weight=0.05,
        category="事业单位",
        notes="广西各高校就业信息网（校招渠道）",
    ),
    SearchSite(
        name="应届生求职网",
        site_domain="yingjiesheng.com",
        priority=3,
        weight=0.02,
        category="综合招聘",
        notes="应届生专属",
    ),
]

# ─── 关键事业单位直连 ─────────────────────────────────────

DIRECT_GOV_SITES: List[SearchSite] = [
    SearchSite(
        name="广西环科院",
        site_domain="gxhky.org.cn",
        priority=1,
        weight=0.5,
        category="事业单位",
        notes="广西环境保护科学研究院官网，招聘公告栏",
    ),
    SearchSite(
        name="广西自然资源厅",
        site_domain="dnr.gxzf.gov.cn",
        priority=1,
        weight=0.5,
        category="事业单位",
        notes="自然资源信息中心/遥感院等直属单位招聘",
    ),
]


def generate_search_queries(
    keywords: str,
    city: str = "广西",
    sites: List[SearchSite] = None,
    max_per_site: int = 5,
) -> List[dict]:
    """生成多平台搜索查询列表
    
    Returns:
        List[dict]: 每个元素包含 site_name, query, site_domain, priority
    """
    if sites is None:
        sites = GUANGXI_SITES
    
    queries = []
    for site in sites:
        # 组合查询：关键词 + 城市 + 招聘 + site限定
        query = f'{keywords} {city} 招聘 site:{site.site_domain}'
        queries.append({
            "site_name": site.name,
            "query": query,
            "site_domain": site.site_domain,
            "priority": site.priority,
            "category": site.category,
            "weight": site.weight,
            "max_results": max_per_site if site.priority <= 2 else 3,
        })
    
    return sorted(queries, key=lambda q: q["priority"])


def generate_direct_queries(
    keywords: str,
    city: str = "广西",
) -> List[dict]:
    """生成事业单位直连查询"""
    queries = []
    for site in DIRECT_GOV_SITES:
        queries.append({
            "site_name": site.name,
            "query": f'{keywords} 招聘 site:{site.site_domain}',
            "site_domain": site.site_domain,
            "priority": 1,
            "category": "事业单位",
            "max_results": 5,
        })
    return queries


def get_verify_queries(company_name: str) -> List[dict]:
    """生成公司验证专用查询"""
    return [
        {
            "site_name": "天眼查",
            "query": f'{company_name} 天眼查 工商信息 注册资本',
            "priority": 1,
            "category": "工商验证",
            "max_results": 3,
        },
        {
            "site_name": "国家企业信用信息公示系统",
            "query": f'{company_name} site:gsxt.gov.cn',
            "priority": 1,
            "category": "工商验证",
            "max_results": 3,
        },
        {
            "site_name": "企业官网",
            "query": f'{company_name} 官方网站',
            "priority": 2,
            "category": "官方渠道",
            "max_results": 3,
        },
        {
            "site_name": "招聘验证",
            "query": f'{company_name} 招聘 site:gxrc.com OR site:zhaopin.com',
            "priority": 2,
            "category": "招聘验证",
            "max_results": 5,
        },
        {
            "site_name": "风险扫描",
            "query": f'{company_name} 失信 被执行 行政处罚',
            "priority": 2,
            "category": "风险扫描",
            "max_results": 3,
        },
    ]
