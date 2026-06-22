# ai-job-hunt 架构文档

## 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI 入口层                               │
│  cli.py: 14 命令 + 3 子命令组，Typer + Rich 双模式              │
│  --json: JSON 机器可读  |  默认: Rich 终端渲染                  │
├─────────────────────────────────────────────────────────────────┤
│                        统一输出层                               │
│  utils/output.py: Output 类                                     │
│  Rich Console 终端模式 ←→ JSON stdout 机器模式                   │
├────────────┬──────────────┬──────────────┬─────────────────────┤
│  信息采集   │   评估匹配    │   管道管理    │     投递应用          │
│            │              │              │                     │
│ scrapers/  │  ai/         │  pipeline/   │  applier/           │
│ ├─ gxrc    │  ├─ brain    │  ├─ merge    │  ├─ auto_apply      │
│ ├─ job51   │  ├─ matcher  │  ├─ dedup    │  └─ filter          │
│ ├─ boss    │  ├─ verifier │  ├─ normalize│                     │
│ ├─ guipin  │  └─ archetype│  └─ liveness │                     │
│ └─ base    │              │              │                     │
│            │  browser_act │              │                     │
│ 外部工具:   │  集成模块     │              │                     │
│ browser-   │              │              │                     │
│ act CLI    │  A-G 八块     │  9态状态机    │  评分门槛           │
│            │  关键词匹配    │  有效期检测   │  黑名单过滤         │
│            │  5原型分类    │  健康检查     │  伦理约束           │
├────────────┴──────────────┴──────────────┴─────────────────────┤
│                        数据核心层                               │
│  models/: Job · Resume · Application (dataclass)               │
│  db/database.py: SQLite (WAL mode, FK, 唯一索引, config KV)     │
├─────────────────────────────────────────────────────────────────┤
│                        外部平台                                 │
│  GXRC · 前程无忧 · BOSS直聘 · 桂聘网 · 15+ 大学环境学院就业网   │
└─────────────────────────────────────────────────────────────────┘
```

## 数据流

```
用户输入关键词 + 城市
       │
       ▼
┌────────────┐    browser-act     ┌────────────┐
│  scan 抓取  │ ───────────────→  │ 招聘平台     │
│            │ ←───────────────  │ GXRC/51job/ │
│            │   Job 对象列表     │ BOSS直聘     │
└─────┬──────┘                   └────────────┘
      │
      ▼ (存入 SQLite，自动去重)
┌────────────┐
│  match 匹配 │ ──→ AI 引擎 (DeepSeek, 可选)
│            │ ──→ 关键词引擎 (本地, 免API)
└─────┬──────┘
      │ (match_score 0-100)
      ▼
┌────────────┐
│  eval 评估  │ ──→ A-G 八块体系
│            │ ──→ 薪资市场对比
│            │ ──→ 合法性检查
└─────┬──────┘
      │ (overall_score 0-5.0)
      ▼
┌────────────┐
│  report    │ ──→ HTML 报告 (report.css 统一样式)
│            │ ──→ JSON 输出 (--json)
└────────────┘
```

## auto 命令执行流程

```
auto -k "Python 开发,环保" -c 南宁
│
├─ [1/4] SCAN
│   └─ 对每个关键词×平台 调用 _run_scraper()
│      ├─ GXRC: browser-act 全浏览器 → JS eval a[href*="/jobDetail/"]
│      ├─ 51job: 全浏览器 → JS eval .joblist-item
│      └─ BOSS: headed 模式 → cookie 复用
│   └─ 自动去重 (_is_dup)
│   └─ 无新岗位时回退数据库已有岗位
│
├─ [2/4] MATCH
│   └─ AI 优先: brain.match_job() (需 API key)
│   └─ 关键词后备: matcher.match() (本地规则引擎)
│   └─ 放宽门槛: 若无满足 min_score 的，取 TOP 15
│
├─ [3/4] EVAL
│   └─ TOP 10 岗位 A-G 八块评估
│   └─ 评估结果写入 db.jobs.eval_score
│
└─ [4/4] REPORT
    └─ _generate_report_v2()
    └─ 自动分类: 环保×计算机 / Python开发 / 数据分析 / 环保水务 / 其他
    └─ 输出 → output/report_{timestamp}.html
```

## 模块职责

| 模块 | 职责 | 关键类/函数 |
|------|------|------------|
| `cli.py` | CLI 入口，14 命令 | `app`, `auto`, `scan`, `match` |
| `scrapers/` | 多平台岗位抓取 | `GxrcScraper`, `Job51Scraper`, `BossScraper` |
| `ai/brain.py` | AI 编排，LLM 调用 | `AIBrain` |
| `ai/matcher.py` | 本地关键词匹配 | `KeywordMatcher` |
| `ai/archetype.py` | 岗位原型分类 | `detect_archetype()` |
| `ai/verifier.py` | 五层公司验证 | `VerifyResult` |
| `pipeline/` | 管道自动化 | `merge`, `dedup`, `normalize`, `liveness` |
| `applier/` | 投递 + 过滤 | `AutoApplier`, `should_filter` |
| `browser_act.py` | browser-act CLI 封装 | `BrowserAct` |
| `utils/output.py` | 双模式输出 | `Output` |
| `utils/config.py` | TOML 配置 | `Config` |
| `db/database.py` | SQLite 操作 | `Database` |
| `models/` | 数据模型 | `Job`, `Resume`, `Application` |
