# 需求文档：AI 智慧求职系统数据来源与工作流

## 一、数据来源架构

```
外部源（只读）                    内部工作区（读写）                 最终产物
──────────────────────────────────────────────────────────────────────────────

E:/CodeProject/               →  input/
  个人技术能力分析报告.md            ├── profile.md          AI 生成的个人画像
  weflow-cli/                      ├── tech-stack.md       技术栈详析
  DataFusion_*/                    ├── projects.md         项目经历摘要
  PCSR-Platform/                   └── skills-inventory.md 技能清单
  NapCatQQ/
  WeChatMsg/                  →  config.toml             用户配置（城市/薪资/岗位）
  ...152+ repos               →  .local/data/resume.db   结构化简历数据

config.toml                   →  workspace/
  [user] 个人信息                   └── instructions.md     用户对 AI 的修改指令
  [preferences] 求职意向
  [ai] API 配置

input/ + workspace/           →  output/
                                  └── 岗位名_公司名_简历.pdf  定制化最终简历
```

---

## 二、信息来源明细

### 2.1 个人信息源（一次性配置）

| 信息 | 来源 | 说明 |
|------|------|------|
| 姓名/手机/邮箱/微信 | `config.toml` → `[user]` 段 | `job-hunt init` 时配置，或手动编辑 |
| 学历/学校/专业/毕业年份 | LLM 解析 `config.toml` + `input/` | AI 从多源交叉推断 |
| 期望城市/岗位/薪资 | `config.toml` → `[preferences]` 段 | 关键词驱动扫描范围 |
| 技能/项目经历/工作年限 | `E:/CodeProject/` 下所有仓库 | AI 分析项目文件夹生成 |

### 2.2 技能与项目源（AI 自动分析）

| 源 | 路径 | 提取内容 |
|----|------|----------|
| 个人技术能力分析报告 | `E:/CodeProject/个人技术能力分析报告.md` | 已汇总的核心技术栈、四大深耕领域、项目清单 |
| 旗舰项目 | `E:/CodeProject/weflow-cli/` | TypeScript/Node.js 后端、MCP Server、微信数据工程 |
| 环境数据融合 | `E:/CodeProject/DataFusion_*/` | Python 科学计算、Fortran 算法、GIS、健康效益 |
| 平台工程 | `E:/CodeProject/PCSR-Platform/`、`EPA_SMAS/` | C#/.NET、Vue.js、云原生、全栈架构 |
| AI/Agent 项目 | `E:/CodeProject/NapCatQQ/`、`AI-Scientist/`、MCP Server 系列 | LLM 应用、Agent 开发、逆向工程 |
| CLAUDE.md | `E:/CodeProject/CLAUDE.md` | 项目级指令、开发习惯、常用工具链 |

### 2.3 已有参考材料

| 文件 | 用途 |
|------|------|
| `E:/CodeProject/个人技术能力分析报告.md` | **核心输入** — 已分析 152+ 仓库，含技术栈画像和项目分类 |
| `E:/CodeProject/求职系统/` | 求职相关调研文档和参考项目 |
| `E:/CodeProject/CLAUDE.md` | 项目级 AI 行为指令 |

---

## 三、input/ 目录生成规则

### 3.1 AI 读取源 → 生成 input/ 的流程

```
1. AI 读取 E:/CodeProject/个人技术能力分析报告.md
2. AI 读取 E:/CodeProject/CLAUDE.md（了解项目上下文）
3. AI 选择性读取关键项目的 README/CLAUDE.md（weflow-cli、DataFusion、PCSR-Platform 等）
4. AI 生成 input/ 下的标准化文件：
```

### 3.2 input/ 文件清单

```
input/
├── profile.md            # 个人画像（一段话概述，含学历/方向/核心能力）
├── tech-stack.md         # 技术栈表格（语言/框架/工具 + 熟练度 + 佐证项目）
├── projects.md           # 项目经历（STAR 格式，每个项目 3-5 行）
├── skills-inventory.md   # 技能清单（分类：编程语言/领域知识/工具链/软技能）
└── job-targets.md        # 目标岗位画像（城市/行业/岗位类型/薪资范围）
```

### 3.3 各文件格式规范

#### profile.md（个人画像）
```markdown
# 个人画像

**姓名**: [从 config.toml 读取]
**学历**: 硕士 - 环境科学与工程 / 计算机应用
**核心方向**: 环境大数据 + AI Agent + 全栈工程
**一句话定位**: 跨学科技术专家 — 环境科学数据建模 × AI 智能体开发 × 全栈工程实践
**求职意向**: 环境信息系统 / 数据分析 / AI 应用开发 @ 广西
**期望薪资**: 8K-15K
```

#### tech-stack.md（技术栈）
```markdown
# 技术栈

| 类别 | 技术 | 熟练度 | 佐证项目 | 年限 |
|------|------|--------|----------|------|
| 语言 | Python | ⭐⭐⭐⭐⭐ | DataFusion, Benmap_Calculator | 5+ |
| 语言 | TypeScript | ⭐⭐⭐⭐ | weflow-cli, NapCatQQ | 3+ |
| 语言 | C# | ⭐⭐⭐ | PCSR-Platform, SMAT | 3+ |
| 框架 | Vue.js | ⭐⭐⭐⭐ | PCSR-Platform 前端 | 3+ |
| 领域 | 大气数据融合 | ⭐⭐⭐⭐⭐ | DataFusion_EPAproject | 5+ |
| 领域 | LLM/Agent | ⭐⭐⭐⭐ | MCP Server 系列 | 2+ |
| ... | ... | ... | ... | ... |
```

#### projects.md（项目经历）
```markdown
# 项目经历

## 1. WeFlow CLI — 微信聊天记录数据分析工具
- **角色**: 独立开发
- **技术栈**: TypeScript, Node.js, SQLCipher, Python
- **亮点**:
  - 逆向微信 NT 数据库（SQLCipher + WCDB），实现本地毫秒级查询
  - Python 脚本集群实现公众号日报/AI 摘要/月度报告自动生成
  - MCP Server 实现微信与 Claude Code 双向桥接
- **成果**: 日均处理 10 万+ 消息，产出自动化报表

## 2. 大气污染数据融合平台 — 环境科学数据工程
- **角色**: 核心开发
- **技术栈**: Python, Fortran, GIS, AWS
- **亮点**:
  - 实现 PM2.5/O3 二维变分同化算法 (Fortran → Python 移植)
  - 构建 CMAQ 模型后处理管线，支持中美多区域
  - 开发健康效益量化工具 (BenMAP Calculator)
- **成果**: 支撑 EPA 项目数据融合需求

...（5-8 个项目）
```

#### job-targets.md（目标岗位画像）
```markdown
# 目标岗位画像

**城市**: 南宁 / 广西
**行业方向**: 环境信息化 / 数据分析 / AI 应用
**岗位类型**: 
  - 环境信息系统工程师（第一优先级）
  - 数据分析师（环境/政务方向）
  - Python/全栈开发（环保行业）
  - AI 应用开发
**薪资**: 8K-15K
**公司偏好**: 事业单位 / 国企 / 环保科技公司
**关键词**: 环境信息系统, 数据分析, Python, 环保, 大气, 人工智能
```

---

## 四、workspace/ 使用规范

### 4.1 定位
`workspace/` 是用户与 AI 的指令交互区。用户在 `instructions.md` 中写修改意见，AI 读取后执行。

### 4.2 workspace/ 文件

```
workspace/
├── instructions.md       # 当前修改指令（用户写给 AI，AI 读取执行后清空）
├── archive/              # 历史指令归档
│   └── 2026-07-02.md
└── .gitkeep
```

### 4.3 instructions.md 格式示例

```markdown
# 修改指令 - 2026-07-02

## 对 input/profile.md
- 学历改成"硕士 - 环境工程（计算机双学位）"
- 一句话定位改为突出"环境+AI"双背景

## 对 input/projects.md
- DataFusion 项目补充：参与了 EPA 的 XXX 项目
- 去掉 SMAT 项目，太旧了

## 整体要求
- 所有"熟练度"列统一用中文：精通/熟练/掌握/了解
- 生成新的 output/简历时，侧重环境信息系统方向
```

### 4.4 工作流

```
用户编辑 workspace/instructions.md
       ↓
AI 读取 instructions.md + input/ 下所有文件
       ↓
AI 执行修改 → 更新 input/（或直接生成 output/）
       ↓
AI 将 instructions.md 归档到 archive/，清空 instructions.md
```

---

## 五、output/ 产出规范

### 5.1 定位
`output/` 存放最终投递用的简历文件，**不提交 git**（已在 `.gitignore`）。

### 5.2 命名规则

```
output/公司名_岗位名_简历.md
output/公司名_岗位名_简历.pdf
```

### 5.3 生成方式

- **CLI**: `job-hunt scan → match → eval → resume <id>`
- **AI 直接操作**: AI 读取 `input/` + `workspace/instructions.md` → 直接生成到 `output/`

---

## 六、AI 初始化流程（首次运行）

```bash
# Step 1: 安装
pip install -e .

# Step 2: CLI 初始化配置
job-hunt init
# → 填写 [user] 信息、[ai] API key、[preferences] 求职意向

# Step 3: AI 生成 input/
# AI 读取 E:/CodeProject/个人技术能力分析报告.md
# AI 读取关键项目的 README/CLAUDE.md
# AI 生成 input/profile.md, tech-stack.md, projects.md, skills-inventory.md, job-targets.md

# Step 4: 用户审核
# 用户查看 input/ 下文件，在 workspace/instructions.md 写修改意见

# Step 5: AI 根据指令调整，产出最终简历到 output/
```

---

## 七、配置敏感信息保护

- `config.toml` 含 API key、手机号、邮箱 → **已 gitignore**
- `.local/` 含 SQLite 数据库（简历+岗位） → **已 gitignore**
- `input/`、`workspace/`、`output/` → **均为 gitignore**（本地工作区）
- `docs/`、`src/`、`config.example.toml` → **提交 git**
