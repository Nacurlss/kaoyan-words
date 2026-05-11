# AI 协作规则

## 回答模式 · 两级分流

### 🔵 常规模式（默认）

简单、局部、非结构性任务，正常思考回答，不激活额外 Skill。

**触发条件：**
- 事实性问题（"XX概念是什么意思"、"这个公式怎么用"）
- 单文件简单操作（格式整理、改错别字、翻译段落）
- 快速查阅（"帮我查一下XX"、"这两个有什么区别"）
- 简短建议（"推荐几个XX"、"怎么看XX"）
- 代码片段和小范围修改

### 🔴 系统分析模式（三道关卡）

复杂、多步骤、需要全面分析的任务。**必须依次执行：brainstorming → writing-plans → 执行 → verification-before-completion**。

**触发条件（满足任一即激活）：**
- 试卷/真题分析、多维度对比研究、系统性知识整理
- 投资研究报告、复杂问题推演、多文件协同处理
- 笔记体系重构
- 用户明确要求："全面分析"、"系统梳理"、"深入看看"、"仔细分析"

**三道关卡执行标准：**
1. **brainstorming** — 理清意图 → 拆解问题边界 → 提出 2-3 种分析路径 → 等待用户确认
2. **writing-plans** — 写执行计划 → 等待用户确认
3. **执行 + verification-before-completion** — 逐步执行，完成后对照需求逐条验证

## Skill 场景映射

| 场景 | 激活的 Skills |
|------|-------------|
| 试卷/真题分析 | `pdf` → `brainstorming` → `writing-plans` → `verification-before-completion` |
| 投资研究 | `brainstorming` → `dispatching-parallel-agents` → `verification-before-completion` |
| 系统性知识整理 | `brainstorming` → `writing-plans` → `verification-before-completion` |
| 长期学习项目 | `planning-with-files` + `brainstorming` |
| 概念/逻辑卡壳 | `systematic-debugging` |
| 扇贝报刊精读 | 常规模式 |
| 数电/集成电路 | 常规模式 或 `systematic-debugging` |
| 表格数据 | `xlsx` |
| Word 文档 | `docx` |
| PDF | `pdf` |

## 快速强制指令

| 指令 | 效果 |
|------|------|
| `直接做` / `跳过计划` | 跳过 brainstorming 和 writing-plans |
| `全面分析` / `系统梳理` | 强制进入三道关卡 |
| `只要结论` | 跳过推导过程 |
| `存到 Obsidian` | 结果写入 `./obsidian/Main/` |

## 禁用 Skill

纯软件开发场景，学习工作区不激活：
`test-driven-development` `subagent-driven-development` `executing-plans` `using-git-worktrees` `finishing-a-development-branch` `requesting-code-review` `receiving-code-review` `writing-skills` `skill-creator` `frontend-design` `simplify` `claude-api` `keybindings-help` `init` `review` `security-review`

## 行为偏好

- 默认中文回复，专业术语（数电/集成电路/经济学）可保留英文
- 对比类内容优先用表格呈现
- 涉及计算需给出推导过程，不直接给答案
- 修改文件前先确认路径和内容，优先用 SearchReplace 而非整文件重写
- 笔记整理产物默认写入 `./obsidian/Main/`，文件名用中文
- 分析结果如有不确定性，标注置信度并建议交叉验证来源
- 报刊词汇笔记格式：`单词 /音标/ — 词性. 中文释义 | 原文例句`
- 数电题目分析：先判断电路类型（组合/时序），再逐步推导，不跳步
