<img src="./banner.png" width="305" align=right />

<div align="center">

<h1>AI Job Hunt <img src="./logo.png" width="80" valign="middle" /></h1>

*纯 CLI · 本地运行 · AI 驱动 · 面向中国招聘市场*

> 你只管说，AI 来做

![Version](https://img.shields.io/badge/version-0.3.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

</div>

<br clear="all">

---

## 目录

- [✨ 近期更新](#-近期更新)
- [Feature](#feature)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
- [Architecture](#architecture)
- [数据来源](#数据来源)
- [问题反馈](#问题反馈)
- [Thanks](#thanks)
- [License](#license)

---

## ✨ 近期更新

<details open>
<summary>v0.3.0 — 多平台抓取 + 全自动闭环 + 关键词匹配引擎（点击展开）</summary>

- ✨ **全自动闭环** — `auto` 命令一键完成 scan → match → eval → report 四步
- ✨ **关键词匹配引擎** — 内置 `KeywordMatcher`，无需 AI API key 也能打分评估
- ✨ **A-G 八块评估** — 角色摘要/简历匹配/级别策略/薪酬调研/简历定制/面试准备/合法性检查
- ✨ **多平台抓取** — GXRC + 51job + BOSS直聘 browser-act 全浏览器模式
- ✨ **大学就业网** — 广西大学·桂林理工·南宁师大·广西民大·华南理工等 15 个渠道
- ✨ **管道自动化** — 去重/合并/状态标准化/岗位有效期 HTTP 检测
- ✨ **智能过滤** — 猎头/黑名单/薪资/培训伪装 5 维拦截
- 🔧 **--json 输出** — 所有命令支持 `--json`，AI 可解析
- 🔧 **report.css** — 统一报告样式模板

</details>

<details>
<summary>v0.2.0 — A-G 评估 + browser-act 集成（点击展开）</summary>

- ✨ browser-act 集成，安全子进程调用（shell=False 防注入）
- ✨ 岗位原型分类器（Python开发/数据分析/AI信息化/环境科技/政府事业）
- ✨ 五层公司交叉验证
- 🔧 CLI 统一为 Typer + Rich，双模式输出（终端/JSON）

</details>

[完整变更记录 →](https://github.com/zhuobichen/ai-job-command-center/commits/main)

---

## Feature

| 分类 | 功能 |
|------|------|
| 🔍 **抓取** | GXRC · 前程无忧 · BOSS直聘 · 桂聘网 · browser-act 全浏览器模式 · stealth-extract 大学就业网 |
| 🎯 **匹配** | AI 匹配（DeepSeek，可选）· 关键词匹配引擎（本地，免 API）· 双引擎自动降级 |
| 📊 **评估** | A-G 八块体系 · 岗位原型分类 · STAR+R 面试故事 · 五层公司验证 · 智能过滤 |
| ⚡ **自动化** | `auto` 全自动闭环 · 多关键词并行搜索 · 城市优先排序 · 数据库去重 |
| 📄 **简历** | AI 优化简历 · STAR 法则 · Markdown/PDF 输出 |
| 🚀 **投递** | 智能投递（评分门槛 + 黑名单过滤）· BOSS直聘发送 |
| 📋 **管道** | 去重 · 状态标准化 (9态) · 有效期 HTTP 检测 · 健康检查 · 追踪合并 |
| 📊 **报告** | 统一 HTML 报告 · report.css 固定样式 · JSON 机器可读 · 交叉分类 |
| 🔒 **隐私** | 纯本地 SQLite · 零网络上传 · 配置文件本地存储 |

---

## Quick Start

> 前置：Python 3.11+ / Chrome 浏览器

**1. 安装**

```bash
git clone https://github.com/zhuobichen/ai-job-command-center.git
cd ai-job-command-center
pip install -e .
```

**2. 初始化**

```bash
python -m job_hunt init                # AI 引导式配置（-y 跳过交互）
```

**3. 开始使用（关键词匹配模式，无需 API key）**

```bash
python -m job_hunt auto -k "Python 开发,环保" -c 南宁
```

**4. AI 增强模式（需要 DeepSeek API key）**

```bash
# 方式一：配置文件 config.toml → [ai] → api_key = "sk-xxx"
# 方式二：环境变量（与 weflow-cli 一致）
export DEEPSEEK_API_KEY="sk-xxx"

python -m job_hunt auto -k "大气环境,数据分析" -c 南宁,广州 --ai
```

> ⚠️ **DeepSeek API key**：配置文件 `config.toml` 中设置或设环境变量 `DEEPSEEK_API_KEY`，与 weflow-cli 共用同一个 key。
>
> 💡 **无需 API key**：系统内置关键词匹配引擎，`auto` 命令默认使用本地匹配器，无需任何 AI API key 即可完成 scan → match → eval → report 全流程。

---

## Command Reference

### 核心命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `init` | 🚀 AI 引导初始化 | `python -m job_hunt init` |
| `auto -k "关键词" -c 城市` | ⚡ 全自动闭环 | `python -m job_hunt auto -k "Python 开发,环保" -c 南宁` |
| `scan -k "关键词" -p 平台` | 🔍 扫描招聘平台 | `python -m job_hunt scan -k "数据分析" -p gxrc` |
| `match` | 🎯 AI/关键词匹配 | `python -m job_hunt match -n 20` |
| `eval <id>` | 📊 A-G 深度评估 | `python -m job_hunt eval 1` |
| `resume <id>` | 📄 生成定制简历 | `python -m job_hunt resume 1 -f md` |
| `apply <id>` | 🚀 智能投递 | `python -m job_hunt apply 1` |
| `report` | 📋 生成报告 | `python -m job_hunt report` |
| `status` | 📊 投递状态 | `python -m job_hunt status --json` |

### 管道管理

| 命令 | 说明 |
|------|------|
| `pipeline liveness -n 50` | 岗位有效期检测 |
| `pipeline dedup` | 跨平台去重 |
| `pipeline health` | 管道健康检查 |

### 配置管理

| 命令 | 说明 |
|------|------|
| `config list` | 查看全部配置 |
| `config get -k ai.api_key` | 获取配置项 |
| `config set -k ai.api_key -v sk-xxx` | 设置配置项 |

### 其他

| 命令 | 说明 |
|------|------|
| `verify <公司>` | 🔍 公司五层交叉验证 |
| `filter <公司>` | ⛔ 黑名单管理 |
| `parse <简历>` | 📄 解析简历 |
| `chat` | 💬 AI 对话模式 |

### 通用选项

| 选项 | 说明 |
|------|------|
| `--json`, `-j` | JSON 输出（AI 模式） |
| `--yes`, `-y` | 跳过交互确认 |
| `--ai` | 启用 AI 评估（需配置 API key） |
| `--dry-run` | 干跑模式（仅扫描不评估） |
| `--min-score`, `-m` | 最低匹配度（默认 30%） |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     CLI (Typer + Rich)                    │
│   init │ scan │ match │ eval │ auto │ resume │ apply ...  │
│                               │                          │
│                    双模式输出层 (utils/output.py)          │
│                     Rich 终端 ←│→ JSON 机器可读            │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │  信息采集层   │  │   评估匹配层   │  │   管道管理层    │  │
│  │             │  │              │  │                │  │
│  │ scrapers/   │  │  ai/         │  │  pipeline/     │  │
│  │ ├─ gxrc.py  │  │  ├─ brain.py  │  │  ├─ merge.py   │  │
│  │ ├─ job51.py │  │  ├─ matcher.py│  │  ├─ dedup.py   │  │
│  │ ├─ boss.py  │  │  ├─ verifier  │  │  ├─ normalize  │  │
│  │ └─ guipin   │  │  └─ archetype │  │  └─ liveness   │  │
│  │             │  │              │  │                │  │
│  │ browser_act │  │  A-G 八块评估  │  │  9态状态机     │  │
│  │ 集成模块     │  │  关键词匹配    │  │  有效期检测    │  │
│  │             │  │  智能过滤     │  │  健康检查      │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                │                   │           │
│  ┌──────┴────────────────┴───────────────────┴────────┐  │
│  │              models/ (数据模型) + db/ (SQLite)      │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  外部工具: browser-act CLI · Playwright · httpx          │
│  平台: GXRC · 前程无忧 · BOSS直聘 · 桂聘网 · 15+大学就业网│
└──────────────────────────────────────────────────────────┘
```

详见 [UPGRADE_PLAN.md](./UPGRADE_PLAN.md) 和 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)

---

## 数据来源

| # | 渠道 | 抓取方式 | 状态 |
|---|------|------|:--:|
| 1 | 广西人才网 gxrc.com | browser-act 全浏览器 JS eval | ✅ |
| 2 | 前程无忧 51job.com | 全浏览器 JS eval `.joblist-item` | ✅ |
| 3 | BOSS直聘 zhipin.com | headed 登录 + cookie 复用 | ✅ |
| 4 | 广西大学·资环材就业（22页） | stealth-extract | ✅ |
| 5 | 桂林理工·环境就业（7页） | stealth-extract | ✅ |
| 6 | 华南理工·环境学院 | stealth-extract | ✅ |
| 7 | 中山大学·环境学院 | WebSearch | ✅ |
| 8 | 广东工业大学·环境学院 | WebSearch | ✅ |
| 9-15 | 更多大学就业网 | 见 `docs/AI查岗路径_资料来源.md` | ✅ |

---

## 问题反馈

- **[GitHub Issues](https://github.com/zhuobichen/ai-job-command-center/issues)** — Bug 报告 / 功能请求

提交时建议附上：操作命令、错误输出、Python 版本和操作系统。

---

## Thanks

| 项目 | 用途 |
|------|------|
| [career-ops](https://github.com/santifer/career-ops) (44K⭐) | A-G 评估体系 · 管道管理 · STAR+R 故事库 · 42种模式参考 |
| [get_jobs](https://github.com/loks666/get_jobs) (2.4K⭐) | 国内招聘平台适配经验 · 反爬策略 · 智能过滤 |
| [browser-act](https://github.com/browseract) | 浏览器自动化 CLI · stealth-extract · 多平台抓取引擎 |
| [DeepSeek](https://deepseek.com/) | AI 评估与简历优化引擎 |
| [Typer](https://typer.tiangolo.com/) + [Rich](https://rich.readthedocs.io/) | CLI 框架与终端美化 |
| [litellm](https://github.com/BerriAI/litellm) | 多模型统一调用接口 |

---

## 🔒 隐私保护

| 维度 | 措施 |
|------|------|
| **数据存储** | 全部本地 SQLite (`data/resume.db`)，简历/投递记录/岗位库均不离开本机 |
| **API key** | 支持环境变量 `DEEPSEEK_API_KEY`（与 weflow-cli 共用同一 key），配置文件 `config.toml` 已在 `.gitignore` 排除 |
| **网络行为** | 仅通过浏览器直连招聘平台抓取岗位；AI 调用仅发送岗位文本和简历摘要，不传输个人身份信息 |
| **伦理约束** | AI 评分 < 4.0/5 的岗位强烈不建议投递；`apply` 命令必须人工确认，绝不自动提交 |
| **版本控制** | `config.toml`、`.env`、`data/`、`output/`、`logs/` 全部在 `.gitignore` 中，不会推送到 GitHub |

> 💡 **与 weflow-cli 一致**：使用同一个 `DEEPSEEK_API_KEY` 环境变量，纯本地运行，零数据上传。

---

## License

MIT License. See [LICENSE](./LICENSE) for details.

> 本工具仅供个人求职辅助使用。请遵守各招聘平台的使用条款，注意控制抓取频率。AI 不会自动提交申请，最终决定权在你。
