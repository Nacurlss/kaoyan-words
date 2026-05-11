import json
from pathlib import Path

import httpx

CACHE_PATH = Path(__file__).parent / "wordlists" / "dict_cache.json"
API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"

_cache = None


def _load_cache() -> dict:
    global _cache
    if _cache is None:
        if CACHE_PATH.exists():
            try:
                _cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                _cache = {}
        else:
            _cache = {}
    return _cache


def _save_cache(cache: dict):
    try:
        CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


async def lookup_word(word: str) -> list[dict]:
    """Look up a word. Returns list of {pos, meaning} dicts.
    Checks local cache first, then queries Free Dictionary API."""
    cache = _load_cache()
    key = word.lower()
    if key in cache:
        return cache[key]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{API_URL}{key}")
            if resp.status_code == 200:
                data = resp.json()
                meanings = data[0].get("meanings", []) if data else []
                result = []
                for m in meanings:
                    pos = m.get("partOfSpeech", "")
                    for d in m.get("definitions", [])[:2]:
                        result.append({
                            "pos": pos,
                            "meaning": d.get("definition", ""),
                        })
                cache[key] = result
                _save_cache(cache)
                return result
    except Exception:
        pass

    return []


def annotate_word_index(word_index: dict) -> dict:
    """Add dictionary meanings to word index entries (synchronous stub).
    For async lookups, use lookup_word() directly in endpoints."""
    return word_index
