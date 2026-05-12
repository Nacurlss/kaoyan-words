#!/usr/bin/env python3
"""Batch-process 考研英语真题 (PDF + DOCX + DOC) into data/processed/sections/

Handles:
  - Single-year PDFs  (2024-2025)
  - Single-year DOCX (2010-2023)
  - Single-year DOC  (1998-2009, legacy .doc format)

Output: data/processed/sections/{year}_{exam_type}/meta.json + section files

Usage: python scripts/build_papers.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.backend.section_splitter import (
    split_pdf, split_text,
    detect_exam_type, extract_year_from_filename, Section,
)
from src.backend.parser import parse_file

OUT_DIR = ROOT / "data" / "processed" / "sections"
ZJ_DIR = ROOT / "data" / "raw" / "exam_papers"

SECTION_ORDER = [
    "use_of_english", "reading_a", "reading_b",
    "reading_c", "writing_a", "writing_b",
]

SECTION_SHORT = {
    "use_of_english": "完形填空",
    "reading_a":      "阅读A",
    "reading_b":      "阅读B",
    "reading_c":      "阅读C_翻译",
    "writing_a":      "写作A",
    "writing_b":      "写作B",
}


def _detect_exam_type_from_name(filename: str) -> str:
    """Detect exam type from filename like '2010年考研英语二真题.docx'."""
    if '英语二' in filename or '英语（二）' in filename:
        return '英语二'
    if '英语一' in filename or '英语（一）' in filename:
        return '英语一'
    return ''


def _write_sections(year: str, exam_type: str, source: str,
                    sections: list[Section]) -> int:
    """Write section files and meta.json. Returns number of sections."""
    if exam_type in ('英语一', '英语二'):
        dir_name = f"{year}_{exam_type}"
    else:
        dir_name = year
    year_dir = OUT_DIR / dir_name
    year_dir.mkdir(parents=True, exist_ok=True)

    present_keys = {s.key for s in sections}
    meta_sections = []

    for idx, key in enumerate(SECTION_ORDER, 1):
        if key not in present_keys:
            continue
        sec = next(s for s in sections if s.key == key)
        filename = f"{idx:02d}_{SECTION_SHORT[key]}.txt"
        filepath = year_dir / filename
        filepath.write_text("\n\n".join(sec.sentences), encoding="utf-8")
        meta_sections.append({
            "key": sec.key,
            "label": sec.label,
            "label_en": sec.label_en,
            "file": filename,
            "sentence_count": len(sec.sentences),
        })

    meta = {"year": year, "type": exam_type, "source": source,
            "sections": meta_sections}
    (year_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(m["sentence_count"] for m in meta_sections)
    labels = ", ".join(m["label"] for m in meta_sections)
    print(f"  ✅ {dir_name}: {len(meta_sections)} sections, "
          f"{total} 段 | {labels}")
    return len(meta_sections)


def process_file(file_path: Path) -> tuple[str, str] | None:
    """Process a single exam file (PDF/DOCX/DOC). Returns (year, exam_type)."""
    name = file_path.name
    year = extract_year_from_filename(name)
    exam_type = _detect_exam_type_from_name(name)

    try:
        text = parse_file(str(file_path))
    except Exception as e:
        print(f"  ⚠ {name}: 解析失败 - {e}")
        return None

    if not text.strip():
        print(f"  ⚠ {name}: 无文本内容")
        return None

    # Get exam type from content if not in filename
    if not exam_type:
        exam_type = detect_exam_type(text)

    # Pre-2010: no 英语一/二 distinction, normalize to 英语一
    if not exam_type or exam_type == '未知':
        exam_type = '英语一'

    sections = split_text(text)
    if not sections:
        print(f"  ⚠ {name}: 未检测到 section，跳过")
        return None

    _write_sections(year, exam_type or '未知', name, sections)
    return (year, exam_type or '未知')


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(
        [f for f in ZJ_DIR.glob("*") if f.suffix.lower() in ('.pdf', '.docx', '.doc')],
        key=lambda f: f.name
    )

    if not files:
        print("❌ 未找到任何试卷文件")
        return

    pdfs = [f for f in files if f.suffix.lower() == '.pdf']
    docxs = [f for f in files if f.suffix.lower() == '.docx']
    docs = [f for f in files if f.suffix.lower() == '.doc']

    print(f"📖 试卷文件: {len(files)} 个 (PDF:{len(pdfs)} DOCX:{len(docxs)} DOC:{len(docs)})")
    print(f"{'─'*55}")

    all_processed: set[tuple[str, str]] = set()
    errors = []

    for f in files:
        result = process_file(f)
        if result:
            all_processed.add(result)
        else:
            errors.append(f.name)

    print(f"\n{'─'*55}")
    print(f"✅ 成功: {len(all_processed)} 个年份-试卷组合")

    if errors:
        print(f"⚠ 失败 ({len(errors)}): {', '.join(errors)}")

    existing = sorted(d.name for d in OUT_DIR.iterdir() if d.is_dir())
    print(f"   输出目录: {', '.join(existing)}")


if __name__ == "__main__":
    build()
