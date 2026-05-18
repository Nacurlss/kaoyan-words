#!/usr/bin/env python3
"""用 DeepSeek API 批量翻译未覆盖词汇 | Translate uncovered words via DeepSeek API.

Input:  data/exports/uncovered_words_final.json
Output: data/exports/uncovered_words_translated.json
Cache:  data/processed/vocab_translations/

按考研大纲风格翻译，标注词性，分批调用 API 并缓存结果。
Usage: python scripts/translate_uncovered_words.py
"""


import hashlib
import json
import os
import re
import time
from pathlib import Path

import dotenv
import requests

ROOT = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(ROOT / ".env")

INPUT_FILE = ROOT / "data" / "exports" / "uncovered_words_final.json"
OUTPUT_FILE = ROOT / "data" / "exports" / "uncovered_words_translated.json"
CACHE_DIR = ROOT / "data" / "processed" / "vocab_translations"

API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/v1/chat/completions"
BATCH_SIZE = 30

VOCAB_PROMPT = """你是考研英语词汇编纂专家。请为下列英语单词提供标准中文释义（考研大纲风格），匹配给定词性。

返回一个JSON对象，key是单词原文，value是 `词性简写|中文释义`。
词性简写：n/v/adj/adv/prep/conj/pron。
中文释义2-6字，只取最核心的考研释义。

只返回JSON，不要解释：

{{
{entries}
}}"""


def make_batch_entries(items: list[dict]) -> str:
    lines = []
    for w in items:
        lines.append(f'  "{w["lemma"]}": "{w["pos"]}|"')
    return ",\n".join(lines)


def cache_key(words: list[str]) -> str:
    raw = json.dumps(sorted(words), ensure_ascii=False)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def cache_get(key: str) -> dict | None:
    p = CACHE_DIR / f"{key}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def cache_put(key: str, data: dict):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def translate_batch(items: list[dict]) -> dict[str, str]:
    lemmas = [w["lemma"] for w in items]
    ck = cache_key(lemmas)
    cached = cache_get(ck)
    if cached:
        return cached

    entries = make_batch_entries(items)
    prompt = VOCAB_PROMPT.format(entries=entries)

    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一个考研英语词汇编纂专家。只返回JSON对象。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        },
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    content = body["choices"][0]["message"]["content"].strip()

    if content.startswith("```"):
        content = re.sub(r'^```[a-z]*\n?', '', content)
        content = re.sub(r'\n?```$', '', content)

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        result = {}
        for line in content.split("\n"):
            m = re.search(r'"(\w+)"\s*:\s*"([^"]+)"', line)
            if m:
                result[m.group(1)] = m.group(2)

    if not isinstance(result, dict):
        result = {}

    cache_put(ck, result)
    return result


def main():
    with open(INPUT_FILE, encoding="utf-8") as f:
        words_data = json.load(f)

    print(f"Total words: {len(words_data)}")
    print(f"Batches: {(len(words_data) + BATCH_SIZE - 1) // BATCH_SIZE} × {BATCH_SIZE}")

    all_results: dict[str, str] = {}
    fresh = 0

    for i in range(0, len(words_data), BATCH_SIZE):
        batch = words_data[i : i + BATCH_SIZE]
        n = i // BATCH_SIZE + 1
        total_batches = (len(words_data) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n  Batch {n}/{total_batches} ({i+1}-{min(i+BATCH_SIZE, len(words_data))})...", end=" ", flush=True)

        try:
            results = translate_batch(batch)
            new_count = 0
            for w in batch:
                lemma = w["lemma"].lower()
                if lemma in results and results[lemma]:
                    all_results[lemma] = results[lemma]
                    new_count += 1
            fresh += new_count
            print(f"ok ({new_count} results)")
        except Exception as e:
            print(f"ERROR: {e}")
            time.sleep(2)

        if i + BATCH_SIZE < len(words_data):
            time.sleep(0.3)

    print(f"\nDone. {fresh} new, {len(all_results)} total.")

    output = []
    for w in words_data:
        lemma = w["lemma"].lower()
        output.append({
            "lemma": w["lemma"],
            "pos": w["pos"],
            "frequency": w["frequency"],
            "total_count": w["total_count"],
            "variants": w.get("variants", []),
            "translation": all_results.get(lemma, ""),
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Exported: {OUTPUT_FILE}")

    translated = [w for w in output if w["translation"]]
    print(f"\nTranslated: {len(translated)}/{len(output)}")
    print(f"\n=== Top 60 ===")
    for w in translated[:60]:
        print(f"  {w['lemma']:22s} {w['pos']:6s} count={w['total_count']:3d}  → {w['translation']}")


if __name__ == "__main__":
    main()
