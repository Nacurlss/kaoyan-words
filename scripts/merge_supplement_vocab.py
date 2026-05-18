#!/usr/bin/env python3
"""Merge DeepSeek translations into momo supplement vocab.

Reads uncovered_words_translated.json, converts to momo vocab format,
writes momo_supplement.json.

Usage: python scripts/merge_supplement_vocab.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT = ROOT / "data" / "exports" / "uncovered_words_translated.json"
OUTPUT = ROOT / "data" / "processed" / "momo_vocab" / "momo_supplement.json"

with open(INPUT, encoding="utf-8") as f:
    translations = json.load(f)

entries = []
for w in translations:
    translation = w.get("translation", "")
    if not translation or "|" not in translation:
        continue

    pos_raw, meaning = translation.split("|", 1)
    pos = pos_raw.strip()
    meaning = meaning.strip()
    if not meaning:
        continue

    entries.append({
        "lemma": w["lemma"],
        "group": "supplement",
        "group_idx": 0,
        "group_title": "真题补充词汇",
        "senses": [{"pos": pos, "meaning": meaning}],
        "examples_en": [],
    })

entries.sort(key=lambda e: e["lemma"])

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

print(f"Merged {len(entries)} words → {OUTPUT}")
print(f"Sample:")
for e in entries[:5]:
    print(f"  {e['lemma']}: {e['senses'][0]['pos']} | {e['senses'][0]['meaning']}")
