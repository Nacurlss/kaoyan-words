# 考研单词频率筛选

> 基于 1998-2024 考研英语一+二真题的词频统计与备考辅助工具

## 一句话介绍

从 **42 套考研英语真题**（英语一+二，192 个 Section）中提取所有单词，按词形还原 + 词性标注后统计频率，关联墨墨背单词释义。支持生词本、句子翻译、按题型筛选（完形/阅读/翻译）。

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt
cd src/frontend && npm install && cd ../..

# 2. 一键启动
./start.sh

# 浏览器打开 http://localhost:5173/
```

## 版本历史

| 版本 | 日期 | 内容 |
|------|------|------|
| **v0.2.1** | 2026-05-13 | 题型筛选（全部/完形/阅读/翻译）、完形填空选项词统计、墨墨未覆盖词汇检索与翻译 |
| v0.2.0 | 2026-05-12 | 英语一+二集成、词形还原、生词本、墨墨释义关联、句子翻译（DeepSeek） |
| v0.1.x | 2026-05-07~08 | 基础词频统计、试卷解析 |

## 主要功能

### 词频统计
- 42 套真题（1998-2024 英语一+英语二），192 个 Section
- NLTK 词形还原 + 不规则词表（187 项）
- `(year, section, exam_type, pos)` 五元组去重，频率 = 出现单元数 / 总单元数

### 墨墨释义关联
- 关联墨墨背单词正序版词库（6,635 词）的释义和例句
- 单词详情展示：真题例句 vs 墨墨原版例句（可切换）

### 题型筛选（v0.2.1 新增）

| 选项 | 内容 | Section |
|------|------|---------|
| 全部题型 | 默认 | 全部 |
| 完形填空 | 文章 + 选项词统计 | `use_of_english` |
| 阅读理解 A+B | 四篇传统阅读 | `reading_a`, `reading_b` |
| 翻译题 | 中英翻译 | `reading_c` |

词频按当前题型覆盖的 section 数重新计算（例如 reading_b 只有 35 套，分母是 35 不是 42）。

### 生词本
- 上传 .xlsx / .txt 生词表，自动去重 + 词形还原 + 匹配真题频率

### 句子翻译
- DeepSeek V4 Flash API 全文翻译，34,923 句全部完成
- 缓存到 `data/processed/translations/`，永不复翻
- 目标词 **加粗高亮** 显示

### 墨墨未覆盖词汇（v0.2.1 新增）
- 检索出 1,975 个墨墨未收录但真题中出现的实词
- DeepSeek 批量翻译（考研大纲风格，带词性标注）
- 导出：`data/exports/uncovered_words_translated.json`

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python + FastAPI (uvicorn, :8000) |
| 前端 | React + TypeScript + Vite (:5173) |
| NLP | NLTK (tokenize, POS tag, lemmatize) |
| 翻译 | DeepSeek V4 Flash API |
| 试卷解析 | python-docx + pdfplumber + textutil |

## 目录结构

```
├── src/
│   ├── backend/          # FastAPI 后端
│   └── frontend/         # React + TypeScript 前端
├── scripts/              # 工具脚本
│   ├── extract_cloze_options.py      # 完形选项词提取
│   ├── find_uncovered_words.py       # 未覆盖词检索
│   ├── deep_clean_uncovered.py       # 词汇清洗
│   └── translate_uncovered_words.py  # 批量翻译
├── data/
│   ├── raw/exam_papers/  # 原始真题 DOCX/PDF
│   ├── processed/
│   │   ├── sections/     # 按 Section 切分的真题文本
│   │   ├── momo_vocab/   # 墨墨词库 JSON
│   │   └── translations/ # 句子翻译缓存
│   └── exports/          # 导出文件（CSV/JSON）
├── docs/
│   ├── 02-design/        # 设计文档
│   ├── 03-devlogs/       # 开发日志
│   └── 05-manual/        # 使用手册
├── .ai/
│   ├── rules.md          # AI 协作规则
│   └── context.md        # 项目上下文（新 AI 接手指南）
└── start.sh              # 一键启动
```

## API 核心端点

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/words?band=all&sort_by=frequency` | 词频列表（分页） |
| GET | `/api/word/{lemma}` | 单词详情 + 例句 |
| GET | `/api/sense_detail?lemma=X&pos=Y` | 特定词性句子列表 |
| GET/PUT | `/api/settings` | 频率阈值、排除词表、题型筛选 |
| POST | `/api/translate/start` | 触发预翻译 |
| GET | `/api/translate/progress` | 翻译进度 |
| POST | `/api/translate/sentences` | 按需翻译 |
| POST | `/api/upload_papers` | 上传试卷 |
| POST | `/api/personal_vocab/upload` | 上传生词本 |
| GET | `/api/personal_words` | 生词列表 |
| GET | `/api/export/csv?band=high` | 导出 CSV |
| GET | `/api/export/excel?band=high` | 导出 Excel |
