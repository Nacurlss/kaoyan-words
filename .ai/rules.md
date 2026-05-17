# AI 协作规则 — 考研单词频率筛选项目

## 代码约定

- **后端 Python**: 无注释（除非复杂逻辑），用 `"""docstrings"""` 描述函数用途
- **前端 TypeScript/React**: 无注释，组件名用 PascalCase，文件名用 PascalCase.tsx
- **import**: 后端相对导入 `from src.backend.xxx`，前端相对导入 `"./components/xxx"`
- **commit**: conventional commits 格式 (`feat:`, `fix:`, `chore:`, `docs:`)
- **文件修改**: 优先用 SearchReplace，不整文件重写
- **编辑前先 Read**: 修改文件前先读取当前内容

## 翻译功能禁区（不要重复踩坑）

1. **不要用 `«»` 标记** — DeepSeek 会换成 `「」`。只用 `**word**`
2. **不要用字符索引高亮** — DeepSeek 算不准。用 `**` 标记法
3. **`_parse_markers` 必须取最后一个 `**` 对** — DeepSeek 可能标多个
4. **清 pycache 后重启** — 修改 `translator.py` 后必须 `rm -rf src/**/__pycache__`
5. **前端翻译请求用 `useEffect([detail])`** — 不能 `useState(()=>{...})`（那时 detail 是 null）

## 关键变量名（后端）

| 变量 | 含义 |
|------|------|
| `_session_word_index` | 全局词索引 `{lemma: {sentences_by_pos: {pos: [{text, word, year, section, exam_type}]}}}` |
| `_session_settings["section_filter"]` | 题型筛选 `"all"|"cloze"|"reading"|"translation"` |
| `SECTION_FILTER_MAP` | 题型 → section key 映射 |
| `_index_cache` | 索引缓存 dict，key=`(section_filter, exclude_levels, exclude_groups, papers)` |
| `_session_settings["exclude_levels"]` | 排除的词表等级 `["primary","zhongkao","gaokao","cet4"]` |
| `_translate_task` | 翻译进度 `{running, done, total, status, current}` |
| `_personal_vocab_words` | 用户上传的生词 set |
| `translator` | `DeepSeekTranslator` 单例 |

## Skill 使用规则

- 新功能/大改动 → 先 `brainstorming` → 再 `writing-plans` → 确认后才执行
- bug 修复 → 直接分析+修复，不需要 brainstorming
- 不要主动用 `subagent-driven-development` 等纯软件 Skill（项目约定：分任务执行）

## 文档位置

| 文档 | 路径 |
|------|------|
| 使用手册 | `docs/05-manual/使用手册.md` |
| 设计文档 | `docs/02-design/` |
| 问题清单 | `docs/04-issues/问题清单.md` |
| 翻译设计 | `docs/02-design/翻译功能设计方案-2026-05-12.md` |
| 翻译计划 | `docs/02-design/翻译功能实现计划-2026-05-12.md` |
| 题型筛选设计 | `docs/02-design/题型筛选功能设计方案-2026-05-13.md` |
| 题型筛选计划 | `docs/02-design/题型筛选功能实现计划-2026-05-13.md` |
| 完形选项设计 | `docs/02-design/完形填空选项词统计设计方案-2026-05-13.md` |
| 未覆盖词检索 | `docs/02-design/墨墨未覆盖词汇检索翻译设计方案-2026-05-13.md` |
| v0.2.1 开发日志 | `docs/03-devlogs/v0.2.1计划-2026-05-13.md` |
| AI 上下文 | `.ai/context.md`（本文件同目录） |
