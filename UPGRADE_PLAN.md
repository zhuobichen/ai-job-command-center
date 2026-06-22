# ai-job-hunt 升级路线图

> 对比 career-ops (44K⭐) + get_jobs (2.4K⭐)，面向广西/广东求职场景的融合升级方案
> 生成时间：2026-06-21

---

## 一、三维对比总览

| 维度 | ai-job-hunt (我们) | career-ops (参比) | get_jobs (参比) |
|------|:---:|:---:|:---:|
| 语言 | Python 3.11 | Node.js | Java 21 |
| 交互 | CLI (Typer+Rich) | Claude Code Modes | Web GUI + CLI |
| 数据库 | SQLite ✅ | Markdown 文件 | MySQL/嵌入式 |
| 平台覆盖 | BOSS直聘 (仅抓取) | Greenhouse/Ashby/Lever 等 | BOSS/51job/猎聘/智联 |
| **广西平台** | ❌ 代码空壳 | ❌ | ❌ |
| AI 评估 | 4维匹配 (0-100) | A-G 八块评估 + 原型分类 | AI匹配 (仅BOSS) |
| 投递 | 半自动 (需手动确认) | ❌ 不投递 (伦理约束) | 全自动投递 |
| 简历生成 | Markdown | PDF (HTML/LaTeX) | 图片简历 |
| 管道管理 | ❌ | ✅ 批量/去重/状态机 | ❌ |
| 面试准备 | 基础问答 | STAR+R 故事库 | ❌ |
| 公司验证 | 五层交叉 ✅ | 合法性检查 | ❌ |
| 自动化 | ❌ | ✅ Loop/Cron 定时扫描 | ✅ 定时投递 |

---

## 二、career-ops 值得我们吸收的10个设计

### 2.1 A-G 八块评估体系（替换当前简单4维）

当前 `brain.py:evaluate_job()` 的6维评估已经部分覆盖，但缺少关键维度：

| 块 | 名称 | 当前状态 | 建议 |
|----|------|:---:|------|
| A | 角色摘要 | ❌ | 新增：原型分类 + 领域 + 职能 + 级别 + 远程 |
| B | 简历匹配 | 半 | 改为逐 JD 要求→简历行号对照表，增加缺失技能弥补方案 |
| C | 级别策略 | ❌ | 新增：JD 要求的级别 vs 你的真实级别，如何卖资历 |
| D | 薪酬市场调研 | ❌ | 新增：WebSearch 查该岗市场薪资区间 |
| E | 简历/LinkedIn 定制 | 半 | `generate_resume()` 已存在，增加5点定制化改动表 |
| F | STAR+R 面试 | ❌ | 新增：6-10个STAR故事 + 反思栏 |
| G | 合法性验证 | 半 | `verifier.py` 已有五层，去掉编造风险 |

### 2.2 岗位原型分类（Archetype Detection）

career-ops 把每个岗位先归入原型，再按原型调整评估策略。针对你的背景，建议原型：

| 原型 | 触发信号 | 策略 |
|------|----------|------|
| Python 开发 | Flask/Django/FastAPI + 后端 | 强调项目经验+自动化脚本 |
| 数据分析 | pandas/numpy/BI | 强调数据融合+PM2.5背景 |
| AI/信息化 | LLM/机器学习/信息化 | 强调AI工具链+LLM应用 |
| 环境科技 | 环境/大气/监测 | 强调专业对口+技术赋能 |
| 政府事业 | 事业编/国企/厅局 | 强调学历+稳定+专业匹配 |

### 2.3 管道完整性（Pipeline Integrity）

career-ops 的5个管道脚本很关键：

```
merge-tracker.mjs    → 合并评估结果到追踪表（防重复）
dedup-tracker.mjs    → 同一岗位出现在多个平台时去重
normalize-statuses.mjs → 投递状态标准化
verify-pipeline.mjs  → 管道健康检查
scan.mjs             → 零 token 扫描（直接调 ATS API）
```

**建议**：在 `src/job_hunt/pipeline/` 下实现 Python 版本。

### 2.4 批量并行处理

career-ops 的 `batch/` 目录展示了批量评估模式：
- 用一个 prompt 模板，spawn N 个无头 worker
- 每个 worker 独立评估一个岗位，写入 `batch/tracker-additions/`
- 最后 merge 回主 tracker

**建议**：利用 Python `asyncio.gather()` 并行调 LLM。

### 2.5 STAR+R 面试故事库

career-ops 的核心创新：每次评估后自动积累 STAR 故事，逐渐形成 5-10 个可复用主故事。

**建议**：建 `data/story_bank.jsonl`，每次 eval 自动追加。

### 2.6 岗位有效期检测（Liveness Check）

career-ops 用 Playwright 实时检测 JD 还在不在线上：
- Apply 按钮还在 → active
- 只有 footer/navbar → closed

**建议**：`scrapers/` 中增加 `liveness.py`。

### 2.7 规范化状态机

career-ops 定义了严格的投递状态流转：

```
Evaluated → Applied → Responded → Interview → Offer
                 ↘ Rejected / Discarded / SKIP
```

**建议**：`models/application.py` 的 status 对齐这8个状态。

### 2.8 伦理约束（Ethical Use）

career-ops 的 AGENTS.md 有强制规则：
- **绝不自动提交申请**，人类最终确认
- 评分 < 4.0/5 的岗位强烈不建议投递
- 质量 > 数量

**建议**：在 `auto_apply.py` 和 CLI 中加入评分门槛和确认步骤。

### 2.9 Portal Scanner

career-ops 的 `portals.yml` 预配置了45+公司，按公司维度搜索（不按关键词）。

**建议**：建 `portals.yml`，预配置广西20+目标企业。

### 2.10 Terminal Dashboard

career-ops 用 Go 写了 TUI Dashboard，可以浏览/筛选/排序管道。

**建议**：用 Python `textual` 库实现 CLI Dashboard。

---

## 三、get_jobs 值得我们吸收的5个设计

### 3.1 智能过滤（Smart Filter）

get_jobs 的过滤能力：
- 过滤不活跃 HR（最后活跃 > 30天）
- 过滤猎头岗位
- 过滤薪资不达标
- 黑名单公司自动跳过

**建议**：`scrapers/boss.py` 解析卡片时增加过滤标记。

### 3.2 持久 Cookie 登录

get_jobs 支持超长 Cookie 持久化，每周只需扫码一次。

**建议**：Playwright 的 `storage_state` 保存/加载登录态。

### 3.3 图片简历发送

get_jobs 在 BOSS 直聘打招呼后自动发图片简历，不等 HR 索要。

### 3.4 企业微信通知

get_jobs 通过企微 Webhook 推送投递进度。

### 3.5 反检测增强

get_jobs 的 `anti-detection.js` 注入了更多反检测代码。

---

## 四、广西/广东专属提升（最重要）

### 4.1 当前缺口：广西平台为零

```
ai-job-hunt/src/job_hunt/scrapers/
├── __init__.py     ✅
├── base.py         ✅ (httpx+BS4 基类)
├── boss.py         ✅ (Playwright)
├── gxrc.py         ❌ 空壳 — 广西人才网，最关键的缺失！
├── job51.py        ❌ 空壳
└── bing.py         ❌ 空壳
```

**必须实现**：

| 平台 | 优先级 | 技术路线 | 理由 |
|------|:---:|------|------|
| 广西人才网 (gxrc.com) | 🔴 P0 | httpx + BS4 (纯HTML) | 广西最大，事业单位/国企/民企全覆盖 |
| 桂聘网 (guipin.com) | 🟡 P1 | httpx + BS4 | 广西本地，中小企多 |
| 广东人才市场 | 🟡 P1 | httpx + BS4 | 广东事业单位 |
| BOSS直聘 (已有) | 🟢 P2 | Playwright | 已有，需增强反爬+过滤 |
| 前程无忧 | 🔵 P3 | Playwright | 大而全 |

### 4.2 广西目标企业库

建议建 `portals.yml`，预配置广西 **30+ 目标单位**：

```yaml
# 事业单位/国企/研究院
- 广西环境保护科学研究院
- 广西生态环境监测中心
- 广西气象局
- 广西环境信息中心
- 南宁市环境监测站
- 广西国土资源信息中心
- ...

# 民企
- 广西新美数据有限公司 (Python 开发，已发现)
- 广西景耀网络科技 (Python 数据分析师)
- 广西东科宁创装备 (软件工程师)
- ...
```

### 4.3 广西特有的搜索关键词

针对广西就业市场，关键词策略：

```python
GUANGXI_KEYWORDS = [
    # Python/开发方向
    "Python 开发", "Python 工程师", "软件开发",
    # 数据方向
    "数据分析", "数据处理", "大数据",
    # AI/信息化方向
    "人工智能", "信息化", "AI", "系统运维",
    # 环境方向（专业对口）
    "环境工程师", "环保工程师", "环境影响评价",
    "环境监测", "环境咨询", "环境数据",
    # 政府事业方向
    "事业编 计算机", "事业编 环境",
    # 通用匹配
    "技术岗", "信息技术",
]
```

### 4.4 城市优先级策略

```python
CITY_PRIORITY = {
    0: ["南宁"],           # 绝对优先
    1: ["柳州", "桂林"],    # 次级
    2: ["玉林", "北海", "钦州", "梧州", "防城港"],  # 可考虑
    3: ["广州", "深圳"],    # 广东（优先找个好平台）
    4: ["全国"],            # 最后手段
}
```

---

## 五、分阶段实施路线图

### Phase 1：打通广西平台（本周，3天）

- [ ] 实现 `scrapers/gxrc.py` — 广西人才网抓取
  - 搜索页 HTML 解析
  - 岗位详情页抓取（完整 JD）
  - 分页遍历
- [ ] 实现 `scrapers/guipin.py` — 桂聘网抓取
- [ ] 增加城市过滤层（`models/job.py` 增加 `province` 字段）
- [ ] 建 `portals.yml` — 广西30+目标企业预配置

### Phase 2：升级评估体系（下周，3天）

- [ ] `brain.py:evaluate_job()` 升级为 A-G 八块评估
  - A: 角色摘要（原型分类）
  - B: 简历逐条匹配（JD要求→简历行号）
  - C: 级别策略
  - D: 薪酬调研（WebSearch 查市场价）
  - E: 简历定制化改动表
  - F: STAR+R 面试准备 + 故事库
  - G: 合法性验证（复用 verifier.py，去掉编造）
- [ ] 建 `data/story_bank.jsonl` — 累积面试故事
- [ ] 评分标准化为 1-5 分制

### Phase 3：管道自动化（下下周，2天）

- [ ] 实现 `pipeline/` 模块
  - `merge_tracker.py` — 合并+去重
  - `dedup_tracker.py` — 跨平台去重（同公司同岗位）
  - `normalize_statuses.py` — 状态标准化
  - `liveness_check.py` — 岗位有效期检测
- [ ] application 状态机对齐 career-ops 规范
- [ ] 加入伦理约束：score < 4.0 不准投/auto_apply 需确认

### Phase 4：自动化运转（后续，2天）

- [ ] 定时扫描：`/loop` cron 每24h扫描所有平台
- [ ] 自动评估：扫描完自动跑 match + eval
- [ ] 报告输出：每日生成 `output/job_report_{date}.html`
- [ ] 企业微信/邮件通知

### Phase 5：高级功能（按需）

- [ ] PDF 简历生成（HTML→WeasyPrint）
- [ ] CLI Dashboard（textual TUI）
- [ ] 批量并行评估（asyncio.gather）
- [ ] Playwright 持久登录态

---

## 六、当前已有且不应重复造轮子的功能

以下 ai-job-hunt 已经实现得很好，不需要改：

| 功能 | 文件 | 评价 |
|------|------|:---:|
| CLI入口 (9个命令) | `cli.py` | ✅ 完整，Typer+Rich |
| SQLite数据层 | `db/database.py` | ✅ 完善，WAL模式+索引 |
| 简历解析 | `ai/brain.py:parse_resume()` | ✅ |
| 简历生成 | `ai/brain.py:generate_resume()` | ✅ STAR法则 |
| 面试准备 | `ai/brain.py:prepare_interview()` | ✅ |
| 打招呼语 | `ai/brain.py:generate_greeting()` | ✅ |
| 五层公司验证 | `ai/verifier.py` | ✅ 创新功能 |
| BOSS直聘抓取 | `scrapers/boss.py` | ✅ 需增强反爬 |
| TOML配置管理 | `utils/config.py` | ✅ |

---

## 七、建议的目录结构调整

```
ai-job-hunt/
├── config.toml                 # (已有，升级)
├── portals.yml                 # 新增：目标企业库
├── cv.md                       # 新增：你的简历源文件
│
├── src/job_hunt/
│   ├── cli.py                  # (已有，增加 batch/liveness 命令)
│   ├── ai/
│   │   ├── brain.py            # (已有，升级为 A-G 评估)
│   │   ├── verifier.py         # (已有)
│   │   └── archetype.py        # 新增：岗位原型分类
│   ├── scrapers/
│   │   ├── base.py             # (已有)
│   │   ├── boss.py             # (已有，增强过滤)
│   │   ├── gxrc.py             # 🔴 新增：广西人才网
│   │   ├── guipin.py           # 🟡 新增：桂聘网
│   │   ├── job51.py            # 🔵 待实现
│   │   └── liveness.py         # 新增：岗位有效期检测
│   ├── pipeline/               # 新增：管道自动化
│   │   ├── merge.py
│   │   ├── dedup.py
│   │   ├── normalize.py
│   │   └── portal_scanner.py
│   ├── applier/
│   │   ├── auto_apply.py       # (已有，加入评分门槛)
│   │   └── filter.py           # 新增：智能过滤(HR活跃度/猎头/薪资)
│   ├── models/                 # (已有)
│   ├── db/                     # (已有)
│   └── utils/
│       ├── config.py           # (已有，扩展到支持 portals)
│       └── display.py          # (已有)
│
├── data/
│   ├── resume.db               # (已有)
│   ├── story_bank.jsonl        # 新增：STAR+R 面试故事库
│   └── scan_history.tsv        # 新增：扫描历史(去重用)
│
└── output/                     # (已有)
    ├── resumes/                # 定制简历输出
    ├── reports/                # 评估报告
    └── job_report_{date}.html  # 每日汇总
```

---

## 八、立即可执行的最小改动

如果时间有限，只改这3处就能马上提升：

1. **搞通广西人才网** → 写 `scrapers/gxrc.py`（httpx+BS4 就够了，不需要 Playwright）
2. **配置好关键词** → `config.toml` 里 keywords 改为广西相关词
3. **评估升级** → `brain.py` 的评估 prompt 从4维改为A-G八块

这三步做完了，整个系统就能自动从广西人才网抓岗位、用升级后的评估体系打分、输出完整报告。
