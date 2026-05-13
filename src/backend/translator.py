"""DeepSeek V4 Flash translator with file cache.

Sentence translations are cached to data/processed/translations/
keyed by md5(sentence + "|" + target_word).

Usage:
    translator = DeepSeekTranslator()
    result = translator.translate(
        sentence="The government has proposed a new policy.",
        target_word="propose"
    )
    print(result.translation)   # "政府提出了一项新的政策。"
    print(result.highlight)     # (2, 4) — start/end char indices
"""

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = ROOT_DIR / "data" / "processed" / "translations"


@dataclass
class TranslationResult:
    original: str
    translation: str
    highlight_start: int
    highlight_end: int


TRANSLATE_PROMPT = """You are a Chinese-English translator specialized in exam papers.
Translate the English sentence to natural Chinese.
In your translation, wrap the Chinese word(s) that translate "{target_word}" with ** markers (like **this**).
Only the exact translation of "{target_word}" — do NOT wrap nearby words.
Return ONLY a JSON object (no markdown, no extra text):
{{"translation": "..."}}

Sentence: {sentence}
Target word: {target_word}"""

BATCH_TRANSLATE_PROMPT = """You are a Chinese-English translator specialized in exam papers.
Translate each English sentence below to natural Chinese.
For each sentence, wrap the Chinese word(s) that translate the given target word with ** markers (like **this**).
Only the exact translation — do NOT wrap nearby words.
Return ONLY a JSON array (no markdown, no extra text), one object per sentence in order:
[{{"translation": "..."}}, ...]

{sentences}"""

BATCH_SIZE = 10


class DeepSeekTranslator:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, sentence: str, target_word: str) -> str:
        raw = f"{sentence}|{target_word}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> Path:
        subdir = CACHE_DIR / key[:2]
        subdir.mkdir(parents=True, exist_ok=True)
        return subdir / f"{key}.json"

    def _cache_get(self, key: str) -> TranslationResult | None:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return TranslationResult(**data)
        except Exception:
            return None

    def _cache_put(self, key: str, result: TranslationResult):
        path = self._cache_path(key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, ensure_ascii=False)

    def _parse_markers(self, translation: str) -> tuple[str, int, int]:
        """Extract ** markers from translation, return (clean_text, start, end).
        Handles **word** and also legacy «word» markers."""
        import re
        m = re.search(r'\*\*(.+?)\*\*', translation)
        if m:
            start = m.start()
            end = m.end() - 4  # remove **...**
            clean = translation[:start] + m.group(1) + translation[m.end():]
            return clean, start, end
        # Fallback: legacy «» markers
        start = translation.find("«")
        end = translation.find("»")
        if start >= 0 and end > start:
            clean = translation[:start] + translation[start+1:end] + translation[end+1:]
            return clean, start, end - 1
        return translation, 0, 0

    def translate(self, sentence: str, target_word: str) -> TranslationResult:
        """Translate a single sentence, preferring cache."""
        key = self._cache_key(sentence, target_word)
        cached = self._cache_get(key)
        if cached:
            return cached

        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set in .env")

        prompt = TRANSLATE_PROMPT.format(
            target_word=target_word, sentence=sentence
        )

        resp = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a translator. Return only JSON."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 200,
            },
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        content = body["choices"][0]["message"]["content"].strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        clean, hs, he = self._parse_markers(data["translation"])
        result = TranslationResult(
            original=sentence,
            translation=clean,
            highlight_start=hs,
            highlight_end=he,
        )
        self._cache_put(key, result)
        return result

    def translate_batch(self, items: list[tuple[str, str]]) -> list[TranslationResult]:
        """Translate multiple sentences in one API call. Uncached items only."""
        uncached = []
        for sentence, target_word in items:
            key = self._cache_key(sentence, target_word)
            cached = self._cache_get(key)
            if cached:
                continue
            uncached.append((sentence, target_word, key))

        if not uncached:
            return []

        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set in .env")

        # Build prompt lines
        lines = []
        for i, (sentence, target_word, _key) in enumerate(uncached, 1):
            lines.append(f'{i}. target="{target_word}": {sentence}')
        prompt = BATCH_TRANSLATE_PROMPT.format(sentences="\n".join(lines))

        resp = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are a translator. Return only JSON."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "max_tokens": 3000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        body = resp.json()
        content = body["choices"][0]["message"]["content"].strip()

        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
        content = content.strip()

        data = json.loads(content)
        if not isinstance(data, list):
            data = [data]

        results = []
        for (sentence, target_word, key), entry in zip(uncached, data):
            clean, hs, he = self._parse_markers(entry["translation"])
            result = TranslationResult(
                original=sentence,
                translation=clean,
                highlight_start=hs,
                highlight_end=he,
            )
            self._cache_put(key, result)
            results.append(result)
        return results

    def collect_items_to_translate(self, word_index: dict) -> list[tuple[str, str]]:
        """Scan word_index and return all unique (sentence, target_word) pairs."""
        seen = set()
        items = []
        for lemma, info in word_index.items():
            for pos, sentences in info.get("sentences_by_pos", {}).items():
                for s in sentences:
                    text = s.get("text", "").strip()
                    word = s.get("word", "").strip()
                    if not text or not word:
                        continue
                    pair = (text, word)
                    if pair not in seen:
                        seen.add(pair)
                        items.append(pair)
        return items

    def batch_translate(
        self,
        items: list[tuple[str, str]],
        progress_callback=None,
        rate_limit: float = 0.0,
    ) -> int:
        """Batch translate with rate limiting. Groups 5 sentences per API call."""
        import time

        fresh = 0
        total = len(items)

        for chunk_start in range(0, total, BATCH_SIZE):
            chunk = items[chunk_start : chunk_start + BATCH_SIZE]
            
            # Count already-cached, call batch API for the rest
            try:
                results = self.translate_batch(chunk)
                fresh += len(results)
            except Exception as e:
                print(f"Warning: batch translate error at {chunk_start}: {e}")

            done = min(chunk_start + BATCH_SIZE, total)
            if progress_callback:
                current = chunk[-1][0][:30] if chunk else ""
                progress_callback(done, total, current)

            if chunk_start + BATCH_SIZE < total:
                time.sleep(rate_limit)

        return fresh


translator = DeepSeekTranslator()

_translate_task = {
    "running": False,
    "done": 0,
    "total": 0,
    "status": "idle",
    "current": "",
}
