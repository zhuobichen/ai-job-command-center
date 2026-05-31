# AI智慧求职系统（job-hunt）

> 🎯 你只管说，AI来做。  
> 纯CLI · 本地运行 · AI驱动 · 面向中国招聘市场

基于 [Career-Ops](https://github.com/santifer/career-ops) (44K⭐) 的AI求职理念 + [Get Jobs](https://github.com/loks666/get_jobs) (2.4K⭐) 的国内平台适配经验，融合打造。

---

## 🚀 快速开始

### 环境要求

- Python 3.11+
- 可用的 LLM API Key（OpenAI / DeepSeek / 通义千问 / 文心一言 等）

### 安装

```bash
# 1. 进入项目目录
cd ai-job-hunt

# 2. 安装依赖
pip install typer rich pydantic tomli tomli-w litellm

# 3. （可选）安装浏览器自动化依赖
pip install playwright
playwright install chromium

# 4. （可选）安装PDF生成依赖
pip install weasyprint
```

### 使用

```bash
# 查看帮助
python -m src.job_hunt.cli --help

# 初始化（AI引导式配置）
python -m src.job_hunt.cli init

# 查看状态
python -m src.job_hunt.cli status
```

---

## 📋 命令一览

| 命令 | 功能 | 示例 |
|------|------|------|
| `init` | 🚀 初始化配置（AI引导式问答） | `job-hunt init` |
| `scan` | 🔍 扫描招聘平台抓取岗位 | `job-hunt scan -k "Python开发" -c 北京` |
| `match` | 🎯 AI智能匹配岗位 | `job-hunt match -n 20 -m 60` |
| `eval` | 📊 六维深度评估 | `job-hunt eval 1` |
| `resume` | 📄 生成定制化简历 | `job-hunt resume 1 -f pdf` |
| `apply` | 🚀 自动投递 | `job-hunt apply 1` |
| `status` | 📊 查看投递状态 | `job-hunt status` |
| `chat` | 💬 AI对话模式 | `job-hunt chat` |
| `parse` | 📄 单独解析简历 | `job-hunt parse resume.pdf` |

---

## 🏗️ 项目结构

```
ai-job-hunt/
├── pyproject.toml          # 项目配置
├── config.toml             # 用户配置（自动生成）
├── data/
│   └── resume.db           # SQLite本地数据库
├── src/
│   └── job_hunt/
│       ├── cli.py          # CLI入口（9个命令）
│       ├── ai/
│       │   └── brain.py    # AI编排层（LLM调用）
│       ├── scrapers/
│       │   └── boss.py     # BOSS直聘抓取器
│       ├── applier/
│       │   └── auto_apply.py # 自动投递引擎
│       ├── models/
│       │   ├── resume.py   # 简历数据模型
│       │   ├── job.py      # 岗位数据模型
│       │   └── application.py # 投递记录模型
│       ├── db/
│       │   └── database.py # SQLite操作
│       └── utils/
│           ├── config.py   # TOML配置管理
│           └── display.py  # Rich终端美化
├── output/                 # 生成的简历文件
└── logs/                   # 运行日志
```

---

## 🔧 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| 编程语言 | Python 3.11+ | AI生态最完善 |
| CLI框架 | Typer + Rich | 美观的命令行输出 |
| LLM调用 | litellm | 统一接口，兼容多种模型 |
| 数据库 | SQLite | 纯本地，零配置 |
| 浏览器自动化 | Playwright | 本地Chromium |
| PDF生成 | WeasyPrint | HTML→PDF |

---

## 🎯 设计理念

**参考 Career-Ops 的核心理念：**
- 🧠 AI分析，人决策 — 系统不会自动投递，最终决定权在你
- 📊 A-F六维评估 — 岗位匹配度、职级定位、薪资、公司质量、成长空间
- 🔍 精准匹配而非海投 — 从数百个岗位筛选出真正值得的

**融入 Get Jobs 的实战经验：**
- 🇨🇳 中国招聘平台适配（BOSS直聘、前程无忧、猎聘等）
- 🛡️ 反爬策略（本地浏览器、频率控制）
- 💬 个性化打招呼语生成

---

## 📝 支持的AI模型

通过 litellm 统一接口，支持：
- OpenAI: gpt-4o / gpt-4o-mini
- Anthropic: claude-3-5-sonnet / claude-3-5-haiku
- DeepSeek: deepseek-chat / deepseek-reasoner
- 通义千问: qwen-turbo / qwen-plus
- 文心一言: ernie-4.0-turbo
- 及任何 OpenAI 兼容接口

---

## ⚠️ 免责声明

- 本工具仅供个人求职辅助使用
- 请遵守各招聘平台的使用条款
- 注意控制抓取频率，避免对平台造成压力
- 数据全部存储在本地，不会上传到任何服务器

---

## 📄 许可

MIT License
