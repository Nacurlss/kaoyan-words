# 学习助手 · 项目配置



## 回答模式 · 两级分流

### 🔵 常规模式（默认）

简单、局部、非结构性任务，正常思考回答，不激活额外 Skill。

**触发条件：**
- 事实性问题（"XX概念是什么意思"、"这个公式怎么用"）
- 单文件简单操作（格式整理、改错别字、翻译段落）
- 快速查阅（"帮我查一下XX"、"这两个有什么区别"）
- 简短建议（"推荐几个XX"、"怎么看XX"）
- 代码片段和小范围修改

---

### 🔴 系统分析模式（三道关卡）

复杂、多步骤、需要全面分析的任务。**必须依次执行：brainstorming → writing-plans → 执行 → verification-before-completion**。

**触发条件（满足任一即激活）：**

- **试卷/真题分析**：批改、解析、薄弱点诊断、得分策略
- **多维度对比研究**：模型对比、投资策略对比、院校/专业对比
- **系统性知识整理**：构建知识框架、整理章节笔记、建立概念关联
- **投资研究报告**：宏观经济分析、行业/公司深度分析、个股研报
- **复杂问题推演**：涉及 3 个以上变量或步骤的推理
- **多文件协同处理**：跨多个文件提取信息并综合分析
- **笔记体系重构**：Obsidian vault 结构优化、标签体系设计
- **用户明确要求**："全面分析"、"系统梳理"、"深入看看"、"仔细分析"

**三道关卡执行标准：**

1. **brainstorming** — 理清意图 → 拆解问题边界 → 列出需覆盖的维度 → 提出 2-3 种分析路径 → **等待用户确认方向**
2. **writing-plans** — 基于确认的方向写执行计划（分步骤、每步产出物、涉及文件）→ **等待用户确认计划**
3. **执行 + verification-before-completion** — 按计划逐步执行，每完成一个关键步骤检查结果，全部完成后对照原始需求逐条验证，出示验证证据

---

## Skill 场景映射表

### 学习场景 → Skills

| 场景 | 激活的 Skills | 说明 |
|------|-------------|------|
| 📄 **试卷/真题分析** | `pdf` → `brainstorming` → `writing-plans` → `verification-before-completion` | 先提取 PDF 内容，再系统分析 |
| 📊 **投资研究** | `brainstorming` → `dispatching-parallel-agents` → `verification-before-completion` | 基本面/技术面/宏观分头并行分析 |
| 📝 **系统性知识整理** | `brainstorming` → `writing-plans` → `verification-before-completion` | 拆解知识结构，分章节整理 |
| 📚 **长期学习项目** | `planning-with-files` + `brainstorming` | 用 task_plan.md 追踪进度，支持 /clear 后恢复 |
| 🔁 **定期复习/检查** | `loop` | 设定定时提醒执行检查任务 |
| 🐛 **概念/逻辑卡壳** | `systematic-debugging` | 定位知识盲点根因，不猜答案 |
| 📰 **扇贝报刊精读** | 常规模式（词汇优先） | 输出格式：生词表（单词/音标/释义/例句）+ 难句解析，写入 `./obsidian/Main/报刊词汇/` |
| 🔌 **数电/集成电路** | 常规模式 或 `systematic-debugging` | 概念题直接答；电路分析/时序逻辑卡壳时用 systematic-debugging 定位盲点 |
| 📋 **处理表格数据** | `xlsx` | 成绩追踪、投资数据、统计表 |
| 📖 **处理 Word 文档** | `docx` | 整理复习资料、阅读教材 |
| 🎯 **处理 PDF** | `pdf` | 提取试卷、教材、论文内容 |
| ⚙️ **调整 Claude Code 配置** | `update-config` | 修改 settings.json、权限、环境变量 |

### 快速决策树

```
收到任务
    │
    ├─ 是 PDF/Word/Excel 文件？ → 先激活对应工具 Skill
    │
    ├─ 触发词含 "全面/系统/深入/仔细分析"？ → 🔴 三道关卡
    ├─ 涉及 3+ 文件 或 3+ 分析维度？ → 🔴 三道关卡
    ├─ 需要长期追踪（>1天）？ → + planning-with-files
    ├─ 需要定时执行？ → + loop
    ├─ 报刊词汇/数电概念？ → 🔵 常规模式（直接输出，不走关卡）
    │
    └─ 都不满足 → 🔵 常规模式
```

### 快速强制指令

用户可用以下指令跳过或强制触发流程：

| 指令 | 效果 |
|------|------|
| `直接做` / `跳过计划` | 跳过 brainstorming 和 writing-plans，直接执行 |
| `全面分析` / `系统梳理` | 强制进入三道关卡 |
| `只要结论` | 跳过推导过程，直接给答案 |
| `存到 Obsidian` | 执行完后将结果写入 `./obsidian/Main/` |

---

## 禁用 Skill 清单

以下 Skills 是纯软件开发场景，**在学习工作区中不激活**：

`test-driven-development` `subagent-driven-development` `executing-plans` `using-git-worktrees` `finishing-a-development-branch` `requesting-code-review` `receiving-code-review` `writing-skills` `skill-creator` `frontend-design` `simplify` `claude-api` `keybindings-help` `init` `review` `security-review`

> 共 16 个禁用。仅当明确涉及写代码项目时才按需激活。

---

## 行为偏好

- 默认中文回复，专业术语（数电/集成电路/经济学）可保留英文
- 对比类内容优先用表格呈现
- 涉及计算需给出推导过程，不直接给答案
- 修改文件前先确认路径和内容，优先用 Edit 而非整文件重写
- 笔记整理产物默认写入 `./obsidian/Main/`，文件名用中文
- 分析结果如有不确定性，标注置信度并建议交叉验证来源
- 报刊词汇笔记格式：`单词 /音标/ — 词性. 中文释义 | 原文例句`
- 数电题目分析：先判断电路类型（组合/时序），再逐步推导，不跳步

---

## 项目目录速查

| 旧路径 | 新路径 |
|--------|--------|
| `backend/` | `src/backend/` |
| `frontend/` | `src/frontend/` |
| `真题/` | `data/raw/exam_papers/` |
| `真题整理/` | `data/processed/sections/` |
| `墨墨单词本/` | `data/processed/momo_vocab/` |
| `工作日志/` | `docs/03-devlogs/` |
| `Problem.md` | `docs/04-issues/问题清单.md` |
| `使用手册.md` | `docs/05-manual/使用手册.md` |

AI 协作规则与项目背景详见 `.ai/rules.md` 和 `.ai/context.md`。

