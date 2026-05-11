#!/usr/bin/env python3
"""Batch-process 考研英语真题 (PDF + DOCX) into 真题整理/ directory.

Handles:
  - Single-year PDFs from 真题/2010-2025考研英语真题/
  - Multi-year DOCX bundles from 真题/ (1986-2009)

Output: 真题整理/<year>/{01_完形填空.txt, ..., meta.json}

Usage: python scripts/build_papers.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.backend.section_splitter import (
    split_pdf, split_text, split_docx_by_year,
    detect_exam_type, extract_year_from_filename, Section,
)

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


def _write_sections(year: str, exam_type: str, source: str,
                    sections: list[Section]) -> int:
    """Write section files and meta.json. Returns number of sections."""
    year_dir = OUT_DIR / year
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
    print(f"  ✅ {year} ({exam_type}): {len(meta_sections)} sections, "
          f"{total} 段 | {labels}")
    return len(meta_sections)


def process_pdf(pdf_path: Path) -> str | None:
    """Process a single-year exam PDF."""
    sections = split_pdf(str(pdf_path))
    if not sections:
        print(f"  ⚠ {pdf_path.name}: 未检测到 section，跳过")
        return None
    year = extract_year_from_filename(pdf_path.name)
    exam_type = detect_exam_type(str(pdf_path))
    _write_sections(year, exam_type, pdf_path.name, sections)
    return year


def process_docx_bundle(docx_path: Path) -> list[str]:
    """Process a multi-year DOCX bundle, splitting by year first."""
    print(f"\n📦 合订本: {docx_path.name}")
    year_blocks = split_docx_by_year(str(docx_path))
    if not year_blocks:
        print(f"  ⚠ 未检测到年份分界")
        return []

    processed = []
    for year, text in year_blocks:
        sections = split_text(text)
        if not sections:
            print(f"  ⚠ {year}: 未检测到 section")
            continue
        exam_type = detect_exam_type(text)
        _write_sections(year, exam_type, docx_path.name, sections)
        processed.append(year)

    print(f"  📊 {docx_path.name}: {len(processed)}/{len(year_blocks)} 年 → "
          f"{', '.join(processed)}")
    return processed


def build():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_processed: list[str] = []

    # ── Phase 1: single-year PDFs ──
    pdf_dir = ZJ_DIR / "2010-2025考研英语真题"
    if pdf_dir.exists():
        pdf_files = sorted(pdf_dir.glob("*.pdf"))
        print(f"📖 单年 PDF: {len(pdf_files)} 个")
        print(f"{'─'*55}")
        for f in pdf_files:
            y = process_pdf(f)
            if y:
                all_processed.append(y)

    # Also process standalone PDFs in 真题/ root
    for f in sorted(ZJ_DIR.glob("*.pdf")):
        y = process_pdf(f)
        if y:
            all_processed.append(y)

    # ── Phase 2: multi-year DOCX bundles ──
    docx_files = sorted(ZJ_DIR.glob("*.docx"))
    if docx_files:
        print(f"\n📦 合订本 DOCX: {len(docx_files)} 个")
        print(f"{'─'*55}")
        for f in docx_files:
            years = process_docx_bundle(f)
            all_processed.extend(years)

    # ── Summary ──
    print(f"\n{'─'*55}")
    print(f"✅ 完成: {len(all_processed)} 个年份")
    print(f"   输出: {OUT_DIR}/")
    existing = sorted(d.name for d in OUT_DIR.iterdir() if d.is_dir())
    print(f"   年份: {', '.join(existing)}")


if __name__ == "__main__":
    build()
