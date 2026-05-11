#!/usr/bin/env python3
"""Extract vocabulary from 墨墨单词本 PDF into structured JSON files.

Output to 墨墨单词本/:
  momo_vocab.json          — merged, all ~7100 entries
  主词条.json              — main section (258 word groups)
  附录-基础词.json          — appendix: basic words
  附录-低频大纲词.json       — appendix: low-freq syllabus
  附录-零频大纲词.json       — appendix: zero-freq syllabus
  附录-低频超纲词.json       — appendix: low-freq extra-syllabus

Usage: python scripts/build_vocab.py [--pdf 墨墨单词本-6776.pdf]
"""

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "processed" / "momo_vocab"
PDF_PATH = ROOT / "data" / "raw" / "墨墨单词本-6776.pdf"

# ── Section page ranges (1-indexed, confirmed from PDF exploration) ──
SECTIONS = [
    ("主词条",         "main",          1,   142),
    ("附录-基础词",     "basic",         143, 238),
    ("附录-低频大纲词", "low_syllabus",  239, 283),
    ("附录-零频大纲词", "zero_syllabus", 284, 379),
    ("附录-低频超纲词", "low_extra",     380, 402),
]

POS_SET = {"n", "v", "adj", "adv", "phrv", "prep", "conj", "pron", "num", "art", "int", "aux"}
POS_RE = re.compile(
    r'^(' + '|'.join(POS_SET) + r')\.\s*(.*)$'
)
WORD_ENTRY_RE = re.compile(
    r'^(\d{1,4})\s+(\w[\w\-]*\w|\w)\s*'
    r'(' + '|'.join(POS_SET) + r')?\.?\s*(.*)$'
)
GROUP_TITLE_RE = re.compile(
    r'^(\d{3})\s+(\w[\w\-]*)\s*——\s*(.+)$'
)

# Lines to skip wholesale
SKIP_LINES = {
    "墨墨背单词 2027墨墨考研深度记忆宝典 全部单词",
    "单词 释义 例句",
    "",
}

def is_page_number(line: str) -> bool:
    return re.match(r'^Page\s+\d+$', line.strip()) is not None

def english_ratio(text: str) -> float:
    if not text:
        return 0
    en = len(re.findall(r'[a-zA-Z]', text))
    total = len(re.sub(r'\s', '', text))
    return en / total if total > 0 else 0

def chinese_ratio(text: str) -> float:
    if not text:
        return 0
    zh = len(re.findall(r'[一-鿿]', text))
    total = len(re.sub(r'\s', '', text))
    return zh / total if total > 0 else 0


def extract_main_section(pages: list) -> list[dict]:
    """Extract vocabulary from the main section (pages 1-142).

    This section has a two-level structure:
      - 258 word groups (001–258), each with a theme title
      - Individual word entries (1–N) within each group

    Key challenge: un-numbered sense lines after "单词 释义 例句" belong
    to the first numbered word entry that follows. We buffer these "orphan"
    senses and prepend them to the next word entry.
    """
    entries: list[dict] = []
    current_group_title = ""
    current_group_num = 0

    def flush_word():
        nonlocal current_lemma, current_senses, current_examples, pending_senses, pending_examples
        if not current_lemma:
            return
        # Prepend any pending orphan senses/examples (accumulated since last group header)
        all_senses = pending_senses + current_senses
        all_examples = pending_examples + current_examples
        entries.append(_make_entry(
            "main", current_group_num, current_group_title,
            current_lemma, _dedupe_senses(all_senses),
            all_examples,
        ))
        current_lemma = ""
        current_senses = []
        current_examples = []
        pending_senses = []
        pending_examples = []

    for page in pages:
        text = page.extract_text()
        if not text:
            continue

        lines = text.split("\n")

        # State for parsing within a group
        current_lemma = ""
        current_senses: list[dict] = []
        current_examples: list[str] = []
        # Orphan senses/examples — belong to next numbered word entry
        pending_senses: list[dict] = []
        pending_examples: list[str] = []

        for line in lines:
            line = line.strip()
            if is_page_number(line) or line in SKIP_LINES:
                continue

            # Group title (new group or page break with same group)
            gm = GROUP_TITLE_RE.match(line)
            if gm:
                flush_word()
                current_group_num = int(gm.group(1))
                current_group_title = f"{gm.group(1)} {gm.group(2)} —— {gm.group(3)}"
                continue

            # Column header — reset orphan buffer for new list of words
            if line == "单词 释义 例句":
                pending_senses = []
                pending_examples = []
                continue

            # Word entry: "N word POS. meaning" or "N word"
            wm = WORD_ENTRY_RE.match(line)
            if wm:
                flush_word()

                current_lemma = wm.group(2).lower()
                pos = wm.group(3)
                rest = wm.group(4) or ""

                if pos and rest:
                    current_senses.append({"pos": pos, "meaning": _clean_meaning(rest)})
                elif pos:
                    pass  # POS but no meaning yet
                elif rest:
                    sm = POS_RE.match(rest)
                    if sm:
                        current_senses.append({"pos": sm.group(1), "meaning": _clean_meaning(sm.group(2))})
                continue

            # Sense line (no leading number): "POS. meaning"
            sm = POS_RE.match(line)
            if sm:
                meaning = _clean_meaning(sm.group(2))
                if meaning:
                    sense = {"pos": sm.group(1), "meaning": meaning}
                    if current_lemma:
                        current_senses.append(sense)
                    else:
                        # Orphan sense — belongs to next numbered word
                        pending_senses.append(sense)
                continue

            # English example — buffer if no word yet, otherwise append
            if line and english_ratio(line) > 0.5:
                if current_lemma:
                    current_examples.append(line)
                else:
                    pending_examples.append(line)

        # Don't flush last word across pages — main section words
        # often span pages; carry pending state implicitly

    # Flush final word
    flush_word()
    return entries


def extract_appendix_section(pages: list, group: str) -> list[dict]:
    """Extract vocabulary from an appendix section."""
    entries: list[dict] = []
    current_lemma = ""
    current_senses: list[dict] = []
    current_examples: list[str] = []
    pending_senses: list[dict] = []
    pending_examples: list[str] = []

    def flush():
        nonlocal current_lemma, current_senses, current_examples, pending_senses, pending_examples
        if not current_lemma:
            return
        all_senses = pending_senses + current_senses
        all_examples = pending_examples + current_examples
        entries.append(_make_entry(
            group, 0, "",
            current_lemma, _dedupe_senses(all_senses),
            all_examples,
        ))
        current_lemma = ""
        current_senses = []
        current_examples = []
        pending_senses = []
        pending_examples = []

    for page in pages:
        text = page.extract_text()
        if not text:
            continue

        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if is_page_number(line) or line in SKIP_LINES:
                continue
            if line.startswith("附录"):
                continue
            if line == "单词 释义 例句":
                pending_senses = []
                pending_examples = []
                continue

            wm = WORD_ENTRY_RE.match(line)
            if wm:
                flush()
                current_lemma = wm.group(2).lower()
                pos = wm.group(3)
                rest = wm.group(4) or ""

                if pos and rest:
                    current_senses.append({"pos": pos, "meaning": _clean_meaning(rest)})
                elif pos:
                    pass
                elif rest:
                    sm = POS_RE.match(rest)
                    if sm:
                        current_senses.append({"pos": sm.group(1), "meaning": _clean_meaning(sm.group(2))})
                continue

            sm = POS_RE.match(line)
            if sm:
                meaning = _clean_meaning(sm.group(2))
                if meaning:
                    sense = {"pos": sm.group(1), "meaning": meaning}
                    if current_lemma:
                        current_senses.append(sense)
                    else:
                        pending_senses.append(sense)
                continue

            if line and english_ratio(line) > 0.5:
                if current_lemma:
                    current_examples.append(line)
                else:
                    pending_examples.append(line)

    flush()
    return entries


def _make_entry(group: str, group_idx: int, group_title: str,
                lemma: str, senses: list[dict], examples: list[str]) -> dict:
    return OrderedDict([
        ("lemma", lemma),
        ("group", group),
        ("group_idx", group_idx),
        ("group_title", group_title),
        ("senses", senses),
        ("examples_en", examples[:5]),  # Keep up to 5 examples
    ])


def _dedupe_senses(senses: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for s in senses:
        key = (s["pos"], s["meaning"])
        if key not in seen:
            seen.add(key)
            result.append({"pos": s["pos"], "meaning": s["meaning"]})
    return result


def _strip_inline_en(text: str) -> str:
    """Strip inline English words from Chinese meanings."""
    if not text:
        return text
    # If text is mostly English, keep as-is
    if english_ratio(text) > 0.5:
        return text.strip()
    # Remove trailing English phrases after Chinese text
    # e.g. "身份 identity card" → "身份"
    result = re.sub(r'([一-鿿])\s+[a-zA-Z].*$', r'\1', text)
    result = re.sub(r'\s*[a-zA-Z][a-zA-Z\s]*$', '', result)
    return result.strip()


def _clean_meaning(raw: str) -> str:
    """Clean a raw meaning string from the PDF.

    Always strips trailing English after Chinese characters.
    """
    text = raw.strip().strip("；; ，,。. ")
    if not text:
        return ""
    # Contains Chinese → strip any trailing English after last Chinese char
    if re.search(r'[一-鿿]', text):
        # Find last Chinese character and cut after it (plus any space)
        m = re.match(r'^([\s\S]*?[一-鿿])\s*[a-zA-Z].*$', text)
        if m:
            text = m.group(1).strip()
        parts = text.split()
        if len(parts) > 1 and re.search(r'[一-鿿]', parts[0]):
            text = parts[0]
    text = text.strip("；; ，,。. ")
    return text


def build(args: list[str]):
    pdf_path = PDF_PATH
    if "--pdf" in args:
        idx = args.index("--pdf")
        pdf_path = Path(args[idx + 1])

    if not pdf_path.exists():
        print(f"错误: 找不到 PDF 文件: {pdf_path}")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📖 读取 PDF: {pdf_path}")
    with pdfplumber.open(str(pdf_path)) as pdf:
        total_pages = len(pdf.pages)
        print(f"   共 {total_pages} 页")

        all_entries: dict[str, list[dict]] = {}
        total_count = 0

        for sec_name, sec_group, start, end in SECTIONS:
            end = min(end, total_pages)
            pages = pdf.pages[start - 1 : end]

            print(f"📝 提取: {sec_name} (第{start}-{end}页) ... ", end="", flush=True)

            if sec_group == "main":
                entries = extract_main_section(pages)
            else:
                entries = extract_appendix_section(pages, sec_group)

            count = len(entries)
            lemma_count = len(set(e["lemma"] for e in entries))
            total_count += count

            print(f"{count} 条 (去重 {lemma_count} 词)")

            # Save individual section file
            out_name = f"{sec_name}.json"
            out_path = OUT_DIR / out_name
            out_path.write_text(
                json.dumps(entries, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            all_entries[sec_name] = entries

    # ── Build merged momo_vocab.json ──
    print(f"\n📦 合并总词库 momo_vocab.json ... ", end="", flush=True)
    merged: dict[str, dict] = {}
    for sec_name, _, _, _ in SECTIONS:
        for entry in all_entries.get(sec_name, []):
            lemma = entry["lemma"]
            if lemma not in merged:
                merged[lemma] = entry
            else:
                # Merge senses — add new senses that aren't duplicates
                existing_senses = {(s["pos"], s["meaning"]) for s in merged[lemma]["senses"]}
                for s in entry["senses"]:
                    if (s["pos"], s["meaning"]) not in existing_senses:
                        merged[lemma]["senses"].append(s)
                        existing_senses.add((s["pos"], s["meaning"]))

    # Re-group and re-index merged entries
    merged_list = list(merged.values())
    merged_list.sort(key=lambda e: (e["group"], e["lemma"]))

    out_path = OUT_DIR / "momo_vocab.json"
    out_path.write_text(
        json.dumps(merged_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # ── Summary ──
    print(f"{len(merged_list)} 条")
    print(f"\n{'='*50}")
    print(f"✅ 词库提取完成！文件输出到: {OUT_DIR}/")
    print(f"{'='*50}")
    print(f"{'分组':<20} {'词条数':>8} {'独立词':>8}")
    print(f"{'-'*40}")
    for sec_name, _, _, _ in SECTIONS:
        entries = all_entries.get(sec_name, [])
        unique = len(set(e["lemma"] for e in entries))
        print(f"{sec_name:<20} {len(entries):>8} {unique:>8}")
    print(f"{'-'*40}")
    print(f"{'合计':<20} {total_count:>8} {len(merged):>8}")


if __name__ == "__main__":
    build(sys.argv)
