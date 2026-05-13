# 项目继承指南 — 2026-05-12 会话状态

> 新来的 AI：读完这个文件你就能接续工作了。
> 最后一个人类消息后，这些是最新的关键内容。

---

## 1. 项目速览

**考研单词频率筛选应用** — 1998-2024 考研英语一+二真题（42套, 192个 Section），统计词频，关联墨墨背单词释义，支持生词本、翻译。

### 核心端口 + 启动

| 服务 | 端口 | 启动方式 |
|------|:---:|------|
| 后端 | 8000 | `uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload` |
| 前端 | 5173 | `cd src/frontend && npm run dev -- --host 0.0.0.0` |
| 一键 | — | `./start.sh` |

`.env` 文件在项目根目录，包含 `DEEPSEEK_API_KEY=sk-d11be38c305042bc8da201a131fda930`

---

## 2. 当前状态（2026-05-12）

### v0.2.0 已完成功能
- 英语一+英语二真题集成（`exam_type` 字段区分）
- 187 项不规则词形还原
- 生词本（上传 xlsx/txt → 自动去重 + 词形还原 + 匹配真题）
- 释义次数可点击 → 弹出历年真题句子列表
- 墨墨释义关联 + 墨墨例句开关
- 英语一/二区分显示（`英语一 · 2024 · 阅读理解A`）
- 各类清洗过滤（中文说明、题目、选项、子弹符号等）

### 🆕 翻译功能（正在跑）

**引擎**: DeepSeek V4 Flash API (`model: deepseek-chat`)
**缓存**: `data/processed/translations/{hash[:2]}/{md5}.json`, key=`md5(sentence+"|"+word)`
**成本**: 全部 34,923 句 < ¥3

**前端翻译显示**:
```
原句: The government has proposed a new policy.
      政府提出了一项新政策。    ← 灰色 #999
      **措施**                  ← 目标词加粗加深 #555
```

**关键修改过的文件**:
```
src/backend/translator.py        ← DeepSeek 翻译 + 缓存
src/frontend/src/components/TranslateLine.tsx   ← 翻译渲染组件
src/frontend/src/components/WordTable.tsx       ← SenseDetailPopover 集成翻译
src/frontend/src/components/PersonalVocabTable.tsx  ← 同上
src/frontend/src/components/WordDetailModal.tsx ← 同上
src/frontend/src/App.tsx          ← 预翻译按钮 + 进度轮询
src/frontend/src/api.ts           ← startPreTranslate, getTranslateProgress, fetchTranslations
src/frontend/src/types.ts         ← Translation, TranslateProgress 类型
src/frontend/src/index.css        ← .translate-line 样式
```

### 正在运行
- **后端**: 端口 8000（已启动）
- **前端**: 端口 5173（已启动）
- **预翻译**: 后台线程正在批量翻译 34,923 句，10句/批。查询进度：`GET /api/translate/progress`

---

## 3. `_parse_markers` 的演进（重要：已经历 3 轮 bug 修复！）

### 最终正确方案（当前代码）:

```python
def _parse_markers(self, translation: str) -> tuple[str, int, int]:
    """Strip ALL ** markers, highlight the LAST **...** pair."""
    import re
    matches = list(re.finditer(r'\*\*(.+?)\*\*', translation))
    if not matches:
        return translation, 0, 0
    last = matches[-1]
    clean = re.sub(r'\*\*(.+?)\*\*', r'\1', translation)
    start = last.start() - 4 * (len(matches) - 1)
    return clean, start, start + len(last.group(1))
```

**关键需求**: DeepSeek 可能在翻译中包多个 `**...**` 对（如 `**根据**成绩等因素**衡量**`），必须：
1. 去掉所有 `**` 标记 → `clean`
2. 高亮最后一个 `**...**` 对 → 目标词

**Prompt 给 DeepSeek 用的是 `**word**` 标记法，不是 `«»` 了！**

### 之前失败的方案（不要再用）:
- ❌ `«»` — DeepSeek 有时换成 `「」`，后端不识别
- ❌ `[start, end]` 字符索引 — DeepSeek 算不准
- ❌ `re.search` 只取第一个 `**` 对 — 当有多个时取错

---

## 4. API 端点清单

### 翻译 API
| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/translate/start` | 触发后台全量预翻译 |
| GET | `/api/translate/progress` | 返回 `{done, total, status, current}` |
| POST | `/api/translate/sentences` | 传入 `[{text, word, lemma}]`，返回翻译字典，key=`"text\|word"` |

### 核心 API
| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/words?band=all&sort_by=frequency` | 词频列表 |
| GET | `/api/word/{lemma}` | 单词详情 + `sentences_by_pos` |
| GET | `/api/sense_detail?lemma=X&pos=Y` | 特定词性的句子列表 |
| GET | `/api/settings` | 频率阈值/排除词表设置 |
| POST | `/api/settings` | 更新设置 |
| POST | `/api/upload_papers` | 上传试卷 |
| POST | `/api/personal_vocab/upload` | 上传生词本 |
| GET | `/api/personal_words` | 生词列表 |

---

## 5. 关键架构决策

1. **翻译缓存 key**: `md5(sentence + "|" + target_word)` — 同一句同一目标词永不重复翻译
2. **缓存目录**: `data/processed/translations/{hash[:2]}/{hash}.json` — 256分发防单目录过大
3. **缓存被 `.gitignore`**: 不提交 GitHub
4. **前端 key 匹配**: `${s.text}|${s.word}` — 与后端 `/api/translate/sentences` 返回一致
5. **去重规则**: `(year, section, exam_type, pos)` 五元组在 analyzer 中
6. **预翻译扫描范围**: `_session_word_index` — 包含所有词，含被过滤词（冗余但覆盖所有场景）

---

## 6. 已知短板 + 可优化项

| 问题 | 严重程度 | 说明 |
|------|:---:|------|
| 翻译高亮偶尔不准 | 低 | `_parse_markers` 取最后一个，但 DeepSeek 可能标错词 |
| 34,923 句太多 | 中 | 大量来自已被基础词过滤的词（如 government/social），可只翻当前可见词 |
| 预翻译速度 | 中 | ~2-5 句/秒，受限于 DeepSeek API 响应时间 |
| PaperList 缺少 key | 低 | React warning，不影响功能 |
| 部分句子含选项/题目残留 | 低 | 清洗已大幅改善，边缘 case 仍有 |
| WordDetailModal 翻译请求 | 低 | 用 `useEffect([detail.sentences_by_pos])` 触发，首次可能 null |

---

## 7. 用户偏好记录

- 不喜欢百度系产品 → 选了 DeepSeek
- 翻译用 `**word**` 标记 → 比 `«»` 更可靠
- 偏好逐词验证翻译效果，而不是盲跑全量
- 文档用中文，代码用英文（无注释，约定俗成）
- 对 UI 细节有明确要求（灰色翻译、加深对应词）
- commit message 用 conventional commits 格式
- 分任务执行，而不是全量自动化

---

## 8. Git 状态

```
当前分支: main
最新 commit: 54d9550 "fix: handle multiple ** pairs in DeepSeek response..."
未 push: 无（所有 commit 均已 push origin/main）
```

---

## 9. 恢复工作流程

新会话接手时，按以下顺序：

```bash
# 1. 确保后端运行
curl -s http://localhost:8000/api/translate/progress  # 检查翻译进度

# 2. 确保前端运行
open http://localhost:5173/

# 3. 如果翻译未跑完且需要加速
# 改 BATCH_SIZE 为更大值（在 translator.py），或者只翻可见词

# 4. 如果要新增功能
# 先读 docs/02-design/ 下的设计文档
# 再读 已解决问题清单.md 了解历史
```
