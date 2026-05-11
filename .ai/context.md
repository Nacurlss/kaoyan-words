# 项目背景速览

## 项目概述

**考研单词频率筛选应用** — 统计 47 年（1986-2024）考研英语一真题中每个单词的出现频率，按高/中/低分级，关联墨墨背单词（6776 词条）的释义和例句。

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | React 19 + TypeScript + Vite |
| 后端 | Python FastAPI |
| 文档解析 | python-docx + pdfplumber |
| 分词/词性 | NLTK (punkt + perceptron tagger + WordNet) |
| 词汇基底 | 墨墨 PDF → JSON（6776 词条） |

## 目录结构

```
Words/
├── .ai/                    ← AI 协作配置
├── src/backend/            ← FastAPI 后端
├── src/frontend/           ← React 前端
├── scripts/                ← 工具脚本
├── data/
│   ├── raw/                ← 原始真题 PDF/DOCX
│   ├── processed/          ← 处理后的数据（sections/、momo_vocab/）
│   └── exports/            ← 导出 CSV/Excel
├── docs/                   ← 按生命周期编号的文档
└── tests/                  ← 测试
```

## 当前进度

- **v1**：核心骨架（墨墨词库提取、题型切分、POS 标注、词频统计、前端展示）
- **v2**：导入 1986-2009 合订本、修复段落塌陷、常考例句列
- **v3**：精修（variants 小写、释义清洗、例句切句加粗、墨墨例句开关）
- **v4**：清洗污染（Directions/选项/粘连词）、修复 start.sh
- **当前**：25 项功能已完成，5 项有残缺，6 项缺失

## 关键文件

| 文件 | 职责 |
|------|------|
| `src/backend/main.py` | API 路由、索引构建、启动加载 |
| `src/backend/analyzer.py` | 词频统计、词形还原、POS 标注 |
| `src/backend/section_splitter.py` | 真题题型切分 + 清洗 |
| `src/frontend/src/App.tsx` | 前端主应用 |
| `scripts/build_vocab.py` | 从墨墨 PDF 提取词库 |
| `scripts/build_papers.py` | 切分真题为题型单元 |
| `start.sh` | 一键启动 |

## 启动方式

```bash
./start.sh
# 前端: http://localhost:5173
# 后端: http://localhost:8000
```

## 待修问题

见 `docs/04-issues/bugs.md`
