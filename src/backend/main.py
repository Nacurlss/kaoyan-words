"""FastAPI backend for 考研单词频率筛选 v2.

Key changes from v1:
- Papers loaded from 真题整理/ directory at startup (pre-split by section)
- Frequency index uses (year, section, pos) triplet dedup
- 墨墨 vocab senses with per-POS occurrence counts
- /api/sense_detail endpoint for drilling into POS-specific examples
- Momo group filtering (exclude_groups setting)
"""

from fastapi import FastAPI, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
import os
import io
import re
import csv
import json

from dotenv import load_dotenv
load_dotenv()
from pathlib import Path

from src.backend.parser import parse_file, extract_english_sentences, extract_year_from_filename
from src.backend.section_splitter import split_pdf, clean_exam_sentences
from src.backend.analyzer import (
    WordAnalyzer,
    apply_basic_word_filter,
    load_word_list,
    classify_by_frequency,
)
from src.backend.dictionary import lookup_word, annotate_word_index
from src.backend.translator import translator, _translate_task

app = FastAPI(title="考研单词频率筛选 v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = WordAnalyzer()
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = Path(__file__).parent / "uploads"
WORDS_DIR = Path(__file__).parent / "wordlists"
PAPERS_DIR = ROOT_DIR / "data" / "processed" / "sections"
MOMO_DIR = ROOT_DIR / "data" / "processed" / "momo_vocab"

UPLOAD_DIR.mkdir(exist_ok=True)

# ── In-memory session state ──
_session_papers: list[dict] = []
_session_word_index: dict = {}
_session_settings = {
    "high_threshold": 0.3,
    "medium_threshold": 0.1,
    "exclude_levels": ["primary", "zhongkao"],
    "exclude_groups": [],
    "use_momo_examples": False,  # toggle: 墨墨原版例句 vs 真题例句
    "personal_vocab_enabled": False,  # toggle: 生词本模式
    "section_filter": "all",
}

SECTION_FILTER_MAP = {
    "all": None,
    "cloze": ["use_of_english"],
    "reading": ["reading_a", "reading_b"],
    "translation": ["reading_c"],
}

_index_cache: dict = {}

# ── Personal vocab ──
_personal_vocab_words: set[str] = set()


def _make_cache_key() -> tuple:
    settings = _session_settings
    return (
        settings.get("section_filter", "all"),
        tuple(sorted(settings.get("exclude_levels", []))),
        tuple(sorted(settings.get("exclude_groups", []))),
        tuple(sorted(
            p["filename"] for p in _session_papers if p.get("enabled", True)
        )),
    )


def _load_momo_groups() -> dict[str, set[str]]:
    """Load momo group → set of lemmas from the split JSON files."""
    groups: dict[str, set[str]] = {}
    if not MOMO_DIR.exists():
        return groups
    for fname in ["附录-基础词.json", "附录-低频大纲词.json",
                   "附录-零频大纲词.json", "附录-低频超纲词.json"]:
        path = MOMO_DIR / fname
        if not path.exists():
            continue
        # Derive group key from filename
        key_map = {
            "附录-基础词.json": "basic",
            "附录-低频大纲词.json": "low_syllabus",
            "附录-零频大纲词.json": "zero_syllabus",
            "附录-低频超纲词.json": "low_extra",
        }
        key = key_map.get(fname, fname)
        with open(path, encoding='utf-8') as f:
            entries = json.load(f)
        groups[key] = {e['lemma'].lower() for e in entries}
    return groups


MOMO_GROUPS = _load_momo_groups()


def _load_papers_from_disk() -> list[dict]:
    """Load pre-split exam papers from 真题整理/ directory."""
    papers = []
    if not PAPERS_DIR.exists():
        return papers

    for exam_dir in sorted(PAPERS_DIR.iterdir()):
        if not exam_dir.is_dir():
            continue
        meta_path = exam_dir / "meta.json"
        if not meta_path.exists():
            continue

        with open(meta_path, encoding='utf-8') as f:
            meta = json.load(f)

        year = meta['year']
        exam_type = meta.get('type', '未知')
        if exam_type == '未知' or not exam_type:
            exam_type = '英语一'  # pre-2010: no 英语一/二 distinction
        for sec in meta['sections']:
            section_file = exam_dir / sec['file']
            if not section_file.exists():
                continue
            
            raw_text = section_file.read_text(encoding='utf-8').strip()
            # Split by double newline, or fallback to single newline if no double exists
            if '\n\n' in raw_text:
                paragraphs = raw_text.split('\n\n')
            else:
                paragraphs = raw_text.split('\n')
                
            sentences = clean_exam_sentences([p.strip() for p in paragraphs if p.strip()])

            papers.append({
                'year': year,
                'section': sec['key'],
                'section_label': sec['label'],
                'exam_type': exam_type,
                'filename': f"{year}_{sec['key']}",  # synthetic filename
                'sentences': sentences,
            })

    return papers


def _get_exclude_words(levels: list[str]) -> set[str]:
    """Get exclude word set using difference logic."""
    all_primary: set[str] = set()
    all_zhongkao: set[str] = set()
    all_gaokao: set[str] = set()
    all_cet4: set[str] = set()

    def _load(name: str) -> set[str]:
        path = WORDS_DIR / name
        if path.exists():
            return load_word_list(str(path))
        return set()

    needed = set(levels)
    if "primary" in needed or "zhongkao" in needed or "gaokao" in needed or "cet4" in needed:
        all_primary = _load("小学英语大纲词汇.txt")
    if "zhongkao" in needed or "gaokao" in needed or "cet4" in needed:
        all_zhongkao = _load("zhongkao.txt")
    if "gaokao" in needed or "cet4" in needed:
        all_gaokao = _load("gaokao.txt")
    if "cet4" in needed:
        all_cet4 = _load("cet4.txt")

    exclude: set[str] = set()
    if "primary" in levels:
        exclude.update(all_primary)
    if "zhongkao" in levels:
        exclude.update(all_zhongkao)
    if "gaokao" in levels:
        exclude.update(all_gaokao - all_zhongkao - all_primary)
    if "cet4" in levels:
        exclude.update(all_cet4 - all_gaokao - all_zhongkao - all_primary)
    if "custom" in levels:
        exclude.update(_load("custom.txt"))

    return exclude


def _build_index() -> dict:
    """Rebuild the full frequency index with section filter and cache."""
    global _session_papers, _session_settings, _index_cache

    cache_key = _make_cache_key()
    if cache_key in _index_cache:
        return _index_cache[cache_key]

    active_papers = [p for p in _session_papers if p.get('enabled', True)]
    if not active_papers:
        return {}

    sf = _session_settings.get("section_filter", "all")
    allowed = SECTION_FILTER_MAP.get(sf)
    if allowed is not None:
        active_papers = [p for p in active_papers if p['section'] in allowed]

    word_index = analyzer.build_frequency_index(active_papers)

    # Momo group filter: only keep words whose group is allowed
    exclude_groups = _session_settings.get('exclude_groups', [])
    if exclude_groups:
        excluded_lemmas = set()
        for g in exclude_groups:
            excluded_lemmas.update(MOMO_GROUPS.get(g, set()))
        word_index = {k: v for k, v in word_index.items() if k not in excluded_lemmas}

    # Basic word filter
    exclude = _get_exclude_words(_session_settings.get('exclude_levels', []))
    if exclude:
        word_index = apply_basic_word_filter(word_index, exclude)

    word_index = annotate_word_index(word_index)

    _index_cache[cache_key] = word_index
    return word_index


def _get_top_example(info: dict, use_momo: bool = False) -> dict | None:
    """Get the most representative example sentence for a word.

    If use_momo is True, returns the first momo example.
    Otherwise picks from the highest-count sense's POS bucket, shortest sentence.
    """
    if use_momo:
        examples = info.get('momo_examples', [])
        if examples:
            return {'text': examples[0], 'word': '', 'year': '墨墨', 'section': '', 'section_label': '墨墨原版例句', 'exam_type': ''}

    senses = info.get('senses', [])
    if not senses:
        return None
    best = max(senses, key=lambda s: s['count'])
    pos = best['pos']
    sents = info.get('sentences_by_pos', {}).get(pos, [])
    if not sents:
        return None
    # Pick shortest sentence (more precise match)
    top = min(sents, key=lambda s: len(s['text']))
    return {
        'text': top.get('text', ''),
        'word': top.get('word', ''),
        'year': top.get('year', ''),
        'section': top.get('section', ''),
        'section_label': top.get('section_label', ''),
        'exam_type': top.get('exam_type', ''),
    }


# ── Startup: load pre-split papers ──
@app.on_event("startup")
async def startup():
    global _session_papers, _session_word_index
    disk_papers = _load_papers_from_disk()
    if disk_papers:
        _session_papers = disk_papers
        _session_word_index = _build_index()
        print(f"✅ 从真题整理/ 加载了 {len(disk_papers)} 个 section 单元")

    import threading
    def warmup():
        for sf in ["all", "cloze", "reading", "translation"]:
            _session_settings["section_filter"] = sf
            _build_index()
        _session_settings["section_filter"] = "all"
        _session_word_index = _build_index()
    threading.Thread(target=warmup, daemon=True).start()


# ── API Routes ──

@app.post("/api/upload")
async def upload_papers(files: list[UploadFile] = File(...)):
    """Upload and parse new exam papers."""
    global _session_papers, _session_word_index

    for file in files:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in (".docx", ".pdf"):
            continue

        tmp_path = UPLOAD_DIR / file.filename
        with open(tmp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            # Try section-split for new uploads
            sections = split_pdf(str(tmp_path))
            year = extract_year_from_filename(file.filename)

            if sections:
                # Add sectioned papers
                for sec in sections:
                    paper_entry = {
                        "year": year,
                        "section": sec.key,
                        "section_label": sec.label,
                        "filename": f"{year}_{sec.key}",
                        "sentences": clean_exam_sentences(sec.sentences),
                        "enabled": True,
                    }
                    _session_papers.append(paper_entry)
            else:
                # Fallback: treat entire file as one paper
                text = parse_file(str(tmp_path))
                sentences = clean_exam_sentences(
                    [s.get("sentence", "") for s in extract_english_sentences(text)]
                )
                paper_entry = {
                    "year": year,
                    "section": "full",
                    "section_label": "全文",
                    "filename": file.filename,
                    "text": text,
                    "sentences": sentences,
                    "enabled": True,
                }
                _session_papers.append(paper_entry)
        finally:
            if tmp_path.exists():
                os.remove(tmp_path)

    _index_cache.clear()
    _session_word_index = _build_index()
    return {"uploaded": len(files), "total_units": len(_session_papers)}


@app.get("/api/papers")
async def get_papers():
    """Get list of loaded papers (grouped by year)."""
    by_year: dict[str, list] = {}
    for p in _session_papers:
        year = p["year"]
        if year not in by_year:
            by_year[year] = []
        by_year[year].append({
            "section": p["section"],
            "section_label": p.get("section_label", ""),
            "sentence_count": len(p.get("sentences", [])),
            "enabled": p.get("enabled", True),
        })

    return [
        {"year": year, "type": "英语一", "sections": sections, "section_count": len(sections)}
        for year, sections in sorted(by_year.items())
    ]


@app.delete("/api/papers/{year}")
async def delete_paper(year: str):
    """Delete all sections for a given year."""
    global _session_papers, _session_word_index
    _session_papers = [p for p in _session_papers if p["year"] != year]
    _index_cache.clear()
    _session_word_index = _build_index()
    return {"deleted": year, "total_units": len(_session_papers)}


@app.put("/api/papers/toggle")
async def toggle_paper(year: str, section: str = "", enabled: bool = True):
    """Toggle paper section inclusion."""
    global _session_papers, _session_word_index
    for p in _session_papers:
        if p["year"] == year and (not section or p["section"] == section):
            p["enabled"] = enabled
    _session_word_index = _build_index()
    return {"year": year, "section": section, "enabled": enabled}


@app.get("/api/words")
async def get_words(
    band: str = Query("all", regex="^(high|medium|low|all)$"),
    sort_by: str = Query("frequency", regex="^(frequency|lemma)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    search: str = Query("", max_length=50),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=500),
):
    """Get word list with per-POS sense counts."""
    global _session_word_index, _session_settings

    if not _session_word_index:
        return {"words": [], "total": 0, "page": page, "page_size": page_size,
                "bands": {"high": 0, "medium": 0, "low": 0}}

    classified = classify_by_frequency(
        _session_word_index,
        _session_settings["high_threshold"],
        _session_settings["medium_threshold"],
    )

    if band == "all":
        words_dict = dict(_session_word_index)
    else:
        words_dict = {k: _session_word_index[k] for k in classified.get(band, [])
                      if k in _session_word_index}

    # Search filter
    if search:
        s = search.lower()
        words_dict = {
            k: v for k, v in words_dict.items()
            if s in k or any(s in var for var in v.get("variants", []))
        }

    # Sort
    reverse = sort_order == "desc"
    if sort_by == "frequency":
        sorted_items = sorted(words_dict.items(), key=lambda x: x[1]["frequency"], reverse=reverse)
    else:
        sorted_items = sorted(words_dict.items(), key=lambda x: x[0], reverse=not reverse)

    # Paginate
    total = len(sorted_items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = sorted_items[start:end]

    return {
        "words": [
            {
                "lemma": lemma,
                "variants": info.get("variants", []),
                "frequency": round(info.get("frequency", 0), 4),
                "senses": info.get("senses", []),
                "pos_counts": info.get("pos_counts", {}),
                "top_example": _get_top_example(
                    info,
                    use_momo=_session_settings.get('use_momo_examples', False)
                ),
                "sentences_by_pos": info.get("sentences_by_pos", {}),
            }
            for lemma, info in page_items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "bands": {
            "high": len(classified.get("high", [])),
            "medium": len(classified.get("medium", [])),
            "low": len(classified.get("low", [])),
        },
    }


@app.get("/api/sense_detail")
async def get_sense_detail(lemma: str, pos: str):
    """Get all (year, section, sentence) records for a lemma+POS combination."""
    global _session_word_index
    info = _session_word_index.get(lemma, {})
    sentences = info.get("sentences_by_pos", {}).get(pos, [])
    pos_units = info.get("pos_units", {}).get(pos, [])

    return {
        "lemma": lemma,
        "pos": pos,
        "unit_count": len(pos_units),
        "sentences": sentences,
    }


@app.get("/api/word/{lemma}")
async def get_word_detail(lemma: str):
    """Get detailed info for a single word."""
    global _session_word_index
    info = _session_word_index.get(lemma)

    if not info:
        meanings = await lookup_word(lemma)
        return {
            "lemma": lemma,
            "variants": [],
            "frequency": 0,
            "senses": [{"pos": m["pos"], "meaning": m["meaning"], "count": 0}
                       for m in meanings],
            "sentences_by_pos": {},
        }

    return {
        "lemma": lemma,
        "variants": info.get("variants", []),
        "frequency": round(info.get("frequency", 0), 4),
        "senses": info.get("senses", []),
        "pos_counts": info.get("pos_counts", {}),
        "sentences_by_pos": info.get("sentences_by_pos", {}),
    }


@app.get("/api/settings")
async def get_settings():
    """Get current settings."""
    return {
        **_session_settings,
        "available_groups": list(MOMO_GROUPS.keys()),
        "group_sizes": {k: len(v) for k, v in MOMO_GROUPS.items()},
    }


@app.put("/api/settings")
async def update_settings(settings: dict):
    """Update settings and rebuild index."""
    global _session_settings, _session_word_index

    for key in ["high_threshold", "medium_threshold", "exclude_levels",
                 "exclude_groups", "use_momo_examples", "personal_vocab_enabled",
                 "section_filter"]:
        if key in settings:
            _session_settings[key] = settings[key]

    _session_word_index = _build_index()
    return _session_settings


# ── Personal Vocab ──

def _normalize_personal_word(raw: str) -> str:
    """Normalize a raw word from personal vocab into its lemma form."""
    from src.backend.analyzer import lemmatize
    w = raw.strip().lower()
    if not w:
        return ""
    return lemmatize(w)


@app.post("/api/personal_vocab/upload")
async def upload_personal_vocab(file: UploadFile = File(...)):
    """Upload a personal vocabulary file (.txt or .xlsx).

    .txt: one word per line.
    .xlsx: first sheet, reads all non-empty cells, filters to English words.

    Words are lemmatized and stored in _personal_vocab_words.
    Returns the parsed word count and preview.
    """
    global _personal_vocab_words

    if not file.filename:
        return {"error": "请选择文件"}

    suffix = Path(file.filename).suffix.lower()

    if suffix == '.txt':
        content = (await file.read()).decode('utf-8', errors='ignore')
        raw_words = [line.strip() for line in content.splitlines() if line.strip()]
    elif suffix == '.xlsx':
        import openpyxl
        import io
        body = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(body))
        ws = wb.active
        raw_words = []
        for row in ws.iter_rows(values_only=True):
            for cell in row:
                if cell and isinstance(cell, str):
                    text = cell.strip()
                    # Only keep cells that look like English words (Latin letters only)
                    if re.match(r'^[A-Za-z]+$', text) and len(text) >= 2:
                        raw_words.append(text)
    else:
        return {"error": "请上传 .txt 或 .xlsx 文件"}

    lemmatized = []
    for w in raw_words:
        lemma = _normalize_personal_word(w)
        if lemma and len(lemma) >= 2:
            lemmatized.append(lemma)

    _personal_vocab_words = set(lemmatized)
    _session_settings["personal_vocab_enabled"] = True

    return {
        "raw_count": len(raw_words),
        "unique_count": len(_personal_vocab_words),
        "preview": sorted(list(_personal_vocab_words))[:30],
    }


@app.get("/api/personal_words")
async def get_personal_words(
    search: str = Query("", max_length=50),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=500),
):
    """Get personal vocab words matched against word index + definitions.

    Each word returns: lemma, frequency in exams, definitions (释义),
    best example sentence from 真题 and from 墨墨.
    """
    global _session_word_index, _personal_vocab_words, _session_settings

    if not _personal_vocab_words:
        return {"words": [], "total": 0, "page": page, "page_size": page_size}

    results = []
    for lemma in sorted(_personal_vocab_words):
        info = _session_word_index.get(lemma, {})

        # Definitions from 墨墨 vocab
        senses = info.get("senses", [])
        if not senses:
            senses = []
            from src.backend.analyzer import MOMO_VOCAB
            momo = MOMO_VOCAB.get(lemma, {})
            for s in momo.get("senses", []):
                senses.append({"pos": s["pos"], "meaning": s["meaning"], "count": 0})

        # Best example from exam papers (真题例句)
        exam_example = None
        top = _get_top_example(info, use_momo=False)
        if top:
            exam_example = {
                "text": top.get("text", ""),
                "year": top.get("year", ""),
                "section_label": top.get("section_label", ""),
                "exam_type": top.get("exam_type", ""),
            }

        # Example from 墨墨
        momo_example = None
        momo_examples = info.get("momo_examples", [])
        if momo_examples:
            momo_example = momo_examples[0]

        freq = info.get("frequency", 0)
        in_exam_papers = len(info.get("variants", [])) > 0 or any(
            v for v in info.get("pos_counts", {}).values()
        )

        results.append({
            "lemma": lemma,
            "frequency": round(freq, 4),
            "in_exam_papers": in_exam_papers,
            "senses": senses,
            "exam_example": exam_example,
            "momo_example": momo_example,
            "pos_counts": info.get("pos_counts", {}),
        })

    # Search filter
    if search:
        s = search.lower()
        results = [r for r in results if s in r["lemma"]]

    # Sort: words found in exams first, then by frequency desc
    results.sort(key=lambda r: (r["in_exam_papers"], r["frequency"]), reverse=True)

    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "words": results[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "vocab_size": len(_personal_vocab_words),
        "matched_count": sum(1 for r in results if r["in_exam_papers"]),
    }


@app.delete("/api/personal_vocab")
async def clear_personal_vocab():
    """Clear the personal vocab list."""
    global _personal_vocab_words
    _personal_vocab_words = set()
    _session_settings["personal_vocab_enabled"] = False
    return {"cleared": True}


# ── Translation ──

@app.post("/api/translate/start")
async def start_pre_translate():
    """Start background pre-translation of all sentences in word_index."""
    global _session_word_index, _translate_task

    if _translate_task["running"]:
        return {"error": "翻译任务已在运行中"}

    items = translator.collect_items_to_translate(_session_word_index)
    _translate_task.update({
        "running": True,
        "done": 0,
        "total": len(items),
        "status": "running",
        "current": "",
    })

    def _run():
        def progress(done, total, current):
            _translate_task.update({
                "done": done,
                "total": total,
                "current": current,
            })
        try:
            translator.batch_translate(items, progress_callback=progress)
            _translate_task["status"] = "done"
        except Exception as e:
            _translate_task["status"] = "error"
            _translate_task["current"] = str(e)
        finally:
            _translate_task["running"] = False

    import threading
    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return {"started": True, "total": len(items)}


@app.get("/api/translate/progress")
async def get_translate_progress():
    """Get pre-translation progress."""
    return _translate_task


@app.post("/api/translate/sentences")
async def get_translations(items: list[dict]):
    """Batch fetch translations for given (sentence, word) pairs.

    Body: [{text: "The...", word: "propose", lemma: "propose"}]
    Returns: {translations: {"text|word": {original, translation, highlight_start, highlight_end}}}
    """
    results = {}
    for item in items:
        try:
            result = translator.translate(
                item.get("text", ""),
                item.get("word", item.get("lemma", "")),
            )
            key = f"{item.get('text', '')}|{item.get('word', item.get('lemma', ''))}"
            results[key] = {
                "original": result.original,
                "translation": result.translation,
                "highlight_start": result.highlight_start,
                "highlight_end": result.highlight_end,
            }
        except Exception:
            pass
    return {"translations": results}


# ── Export ──

@app.get("/api/export/csv")
async def export_csv(band: str = Query("all", regex="^(high|medium|low|all)$")):
    """Export word list as CSV."""
    global _session_word_index, _session_settings

    classified = classify_by_frequency(
        _session_word_index,
        _session_settings["high_threshold"],
        _session_settings["medium_threshold"],
    )
    words = {k: _session_word_index[k] for k in classified.get(band, [])
             if k in _session_word_index} if band != "all" else _session_word_index

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["单词", "变体", "词性", "释义", "次数", "频率"])

    for lemma, info in sorted(words.items(), key=lambda x: x[1].get("frequency", 0), reverse=True):
        senses = info.get("senses", [])
        sense_str = "; ".join(
            f"{s.get('pos', '')}. {s.get('meaning', '')} ({s.get('count', 0)}次)"
            for s in senses[:5]
        ) if senses else ""

        writer.writerow([
            lemma,
            ", ".join(info.get("variants", [])),
            "",
            sense_str,
            sum(info.get("pos_counts", {}).values()),
            round(info.get("frequency", 0), 4),
        ])

    output.seek(0)
    sf = _session_settings.get("section_filter", "all")
    sf_label = {"all": "all", "cloze": "cloze", "reading": "reading",
                "translation": "translation"}.get(sf, "all")
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=words_{sf_label}_{band}.csv"},
    )


@app.get("/api/export/excel")
async def export_excel(band: str = Query("all", regex="^(high|medium|low|all)$")):
    """Export word list as Excel."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side

    global _session_word_index, _session_settings

    classified = classify_by_frequency(
        _session_word_index,
        _session_settings["high_threshold"],
        _session_settings["medium_threshold"],
    )
    words = {k: _session_word_index[k] for k in classified.get(band, [])
             if k in _session_word_index} if band != "all" else _session_word_index

    wb = Workbook()
    ws = wb.active
    ws.title = f"{band}频词汇"

    headers = ["单词", "总次数", "频率", "释义（按词性）", "真题例句"]
    header_font = Font(bold=True, size=12)
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center")

    for row, (lemma, info) in enumerate(
        sorted(words.items(), key=lambda x: x[1].get("frequency", 0), reverse=True), 2
    ):
        senses = info.get("senses", [])
        meaning_str = "; ".join(
            f"{s.get('pos', '')}. {s.get('meaning', '')} ({s.get('count', 0)})"
            for s in senses[:5]
        ) if senses else ""

        # Build sentence preview
        sentence_parts = []
        for pos, sents in info.get("sentences_by_pos", {}).items():
            for s in sents[:1]:
                sentence_parts.append(f"[{s.get('year', '')}·{s.get('section_label', '')}] "
                                     f"{s['text'][:80]}")
        sentence_str = "\n".join(sentence_parts[:5])

        total_count = sum(info.get("pos_counts", {}).values())

        for col, val in enumerate([
            lemma, total_count,
            round(info.get("frequency", 0), 4),
            meaning_str,
            sentence_str[:500],
        ], 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = thin_border
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    for col, w in zip("ABCDE", [18, 10, 10, 50, 60]):
        ws.column_dimensions[col].width = w

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    sf = _session_settings.get("section_filter", "all")
    sf_label = {"all": "all", "cloze": "cloze", "reading": "reading",
                "translation": "translation"}.get(sf, "all")
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=words_{sf_label}_{band}.xlsx"},
    )


# Serve frontend
frontend_build = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="frontend")
