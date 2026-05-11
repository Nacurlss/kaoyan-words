"""Word frequency analyzer for 考研英语真题.

v2: (year, section, pos) triplet dedup, NLTK POS tagging, 墨墨 vocab senses.
"""

import json
import re
import ssl
from collections import defaultdict
from pathlib import Path

import nltk
from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag

# Fix SSL for NLTK downloads on macOS
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

for resource in ['punkt_tab', 'averaged_perceptron_tagger_eng', 'wordnet']:
    try:
        nltk.data.find(f'taggers/{resource}' if 'tagger' in resource else
                       f'tokenizers/{resource}' if 'punkt' in resource else
                       f'corpora/{resource}')
    except LookupError:
        print(f"⚠ NLTK resource missing: {resource}. Run ./start.sh with network access to download it.")

ROOT = Path(__file__).resolve().parent.parent.parent
MOMO_PATH = ROOT / "data" / "processed" / "momo_vocab" / "momo_vocab.json"

# ── Stop words ──
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "will", "would", "shall", "should", "may", "might", "can", "could",
    "must", "i", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their",
    "this", "that", "these", "those",
    "and", "but", "or", "not", "no", "nor",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "about", "into", "through", "during", "before", "after",
    "above", "below", "between", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "only", "own", "same", "so", "than", "too", "very",
    "just", "because", "if", "while", "although", "though",
    "what", "which", "who", "whom", "whose",
    "also", "up", "out", "off", "over", "down",
    "one", "two", "three", "per", "much", "many",
    "new", "first", "last", "long", "great", "little",
    "said", "like", "make", "know", "get", "see", "go", "come",
    "take", "think", "say", "use", "find", "give", "tell",
    "work", "call", "try", "ask", "seem", "feel", "become", "leave",
    "put", "mean", "keep", "let", "begin", "show", "hear",
    "play", "run", "move", "live", "believe", "hold",
    "bring", "happen", "write", "provide", "sit", "stand",
    "lose", "pay", "meet", "include", "continue", "set",
    "learn", "change", "lead", "understand", "watch",
    "follow", "stop", "create", "speak", "read", "allow",
    "add", "spend", "grow", "open", "walk", "win", "offer",
    "remember", "love", "consider", "appear", "buy", "wait",
    "serve", "die", "send", "expect", "build", "stay", "fall",
    "cut", "reach", "kill", "remain", "yet",
    "re", "ve", "ll",
    # Exam instruction word (appears in every section's "Directions:")
    "direction",
}

# Penn Treebank → simple POS
PTB_TO_SIMPLE = {
    'VB': 'v', 'VBD': 'v', 'VBG': 'v', 'VBN': 'v', 'VBP': 'v', 'VBZ': 'v',
    'NN': 'n', 'NNS': 'n', 'NNP': 'n', 'NNPS': 'n',
    'JJ': 'adj', 'JJR': 'adj', 'JJS': 'adj',
    'RB': 'adv', 'RBR': 'adv', 'RBS': 'adv',
    'IN': 'prep', 'TO': 'prep', 'RP': 'adv',
    'DT': 'det', 'PRP': 'pron', 'PRP$': 'pron', 'WP': 'pron',
    'CC': 'conj', 'CD': 'num', 'MD': 'aux',
    'UH': 'int',
}

# ── Irregular lemma dictionary ──
IRREGULAR_LEMMAS = {
    'ran': 'run', 'running': 'run', 'runs': 'run',
    'was': 'be', 'were': 'be', 'been': 'be', 'being': 'be',
    'had': 'have', 'has': 'have', 'having': 'have',
    'did': 'do', 'done': 'do', 'doing': 'do', 'does': 'do',
    'went': 'go', 'gone': 'go', 'going': 'go', 'goes': 'go',
    'said': 'say', 'saying': 'say', 'says': 'say',
    'made': 'make', 'making': 'make', 'makes': 'make',
    'took': 'take', 'taken': 'take', 'taking': 'take', 'takes': 'take',
    'came': 'come', 'coming': 'come', 'comes': 'come',
    'saw': 'see', 'seen': 'see', 'seeing': 'see', 'sees': 'see',
    'knew': 'know', 'known': 'know', 'knowing': 'know', 'knows': 'know',
    'got': 'get', 'gotten': 'get', 'getting': 'get', 'gets': 'get',
    'gave': 'give', 'given': 'give', 'giving': 'give', 'gives': 'give',
    'found': 'find', 'finding': 'find', 'finds': 'find',
    'thought': 'think', 'thinking': 'think', 'thinks': 'think',
    'told': 'tell', 'telling': 'tell', 'tells': 'tell',
    'became': 'become', 'becoming': 'become', 'becomes': 'become',
    'left': 'leave', 'leaving': 'leave', 'leaves': 'leave',
    'felt': 'feel', 'feeling': 'feel', 'feels': 'feel',
    'put': 'put', 'putting': 'put', 'puts': 'put',
    'brought': 'bring', 'bringing': 'bring', 'brings': 'bring',
    'began': 'begin', 'begun': 'begin', 'beginning': 'begin', 'begins': 'begin',
    'kept': 'keep', 'keeping': 'keep', 'keeps': 'keep',
    'held': 'hold', 'holding': 'hold', 'holds': 'hold',
    'wrote': 'write', 'written': 'write', 'writing': 'write', 'writes': 'write',
    'stood': 'stand', 'standing': 'stand', 'stands': 'stand',
    'lost': 'lose', 'losing': 'lose', 'loses': 'lose',
    'paid': 'pay', 'paying': 'pay', 'pays': 'pay',
    'met': 'meet', 'meeting': 'meet', 'meets': 'meet',
    'set': 'set', 'setting': 'set', 'sets': 'set',
    'led': 'lead', 'leading': 'lead', 'leads': 'lead',
    'spent': 'spend', 'spending': 'spend', 'spends': 'spend',
    'built': 'build', 'building': 'build', 'builds': 'build',
    'sent': 'send', 'sending': 'send', 'sends': 'send',
    'won': 'win', 'winning': 'win', 'wins': 'win',
    'fell': 'fall', 'fallen': 'fall', 'falling': 'fall', 'falls': 'fall',
    'cut': 'cut', 'cutting': 'cut', 'cuts': 'cut',
    'read': 'read', 'reading': 'read', 'reads': 'read',
    'spoke': 'speak', 'spoken': 'speak', 'speaking': 'speak', 'speaks': 'speak',
    'drove': 'drive', 'driven': 'drive', 'driving': 'drive', 'drives': 'drive',
    'ate': 'eat', 'eaten': 'eat', 'eating': 'eat', 'eats': 'eat',
    'grew': 'grow', 'grown': 'grow', 'growing': 'grow', 'grows': 'grow',
    'rose': 'rise', 'risen': 'rise', 'rising': 'rise', 'rises': 'rise',
    'threw': 'throw', 'thrown': 'throw', 'throwing': 'throw', 'throws': 'throw',
    'wore': 'wear', 'worn': 'wear', 'wearing': 'wear', 'wears': 'wear',
    'chose': 'choose', 'chosen': 'choose', 'choosing': 'choose',
    'broke': 'break', 'broken': 'break', 'breaking': 'break', 'breaks': 'break',
    'caught': 'catch', 'catching': 'catch', 'catches': 'catch',
    'dealt': 'deal', 'dealing': 'deal', 'deals': 'deal',
    'forgot': 'forget', 'forgotten': 'forget', 'forgetting': 'forget',
    'meant': 'mean', 'meaning': 'mean', 'means': 'mean',
    'sold': 'sell', 'selling': 'sell', 'sells': 'sell',
    'taught': 'teach', 'teaching': 'teach', 'teaches': 'teach',
    'drew': 'draw', 'drawn': 'draw', 'drawing': 'draw',
    'flew': 'fly', 'flown': 'fly', 'flying': 'fly',
}

# NLTK WordNet lemmatizer as fallback
from nltk.stem import WordNetLemmatizer
_wnl = WordNetLemmatizer()


def _clean_momo_meaning(raw: str) -> str:
    """Keep only POS meaning text; strip examples accidentally parsed inline."""
    text = (raw or "").strip()
    if not text:
        return ""

    text = re.sub(r'\s+[A-Z][A-Za-z].*$', '', text).strip()
    parts = text.split()
    if len(parts) > 1 and re.search(r'[一-鿿]', parts[0]):
        text = parts[0]

    return text.strip("；; ，,。. ")


def _load_momo_vocab() -> dict[str, dict]:
    """Load 墨墨 vocab → {lemma: {senses: [...], examples_en: [...]}}."""
    if not MOMO_PATH.exists():
        return {}
    with open(MOMO_PATH, encoding='utf-8') as f:
        entries = json.load(f)
    result: dict[str, dict] = {}
    for e in entries:
        lemma = e['lemma'].lower()
        senses = []
        for s in e.get('senses', []):
            sense = {'pos': s['pos'], 'meaning': _clean_momo_meaning(s['meaning'])}
            if sense not in senses:
                senses.append(sense)
        if lemma not in result:
            result[lemma] = {'senses': senses, 'examples_en': e.get('examples_en', [])}
        else:
            # Merge: add new senses
            existing = {(s['pos'], s['meaning']) for s in result[lemma]['senses']}
            for s in senses:
                if (s['pos'], s['meaning']) not in existing:
                    result[lemma]['senses'].append(s)
    return result


MOMO_VOCAB = _load_momo_vocab()


def lemmatize(word: str) -> str:
    """Lemmatize using NLTK WordNet + irregular dictionary fallback."""
    w = word.lower().strip()
    if w in IRREGULAR_LEMMAS:
        return IRREGULAR_LEMMAS[w]
    # Try WordNet (noun first, since most content words default to noun)
    try:
        lemma = _wnl.lemmatize(w, 'n')
        if lemma != w:
            return lemma
        lemma = _wnl.lemmatize(w, 'v')
        if lemma != w:
            return lemma
        lemma = _wnl.lemmatize(w, 'a')
        if lemma != w:
            return lemma
    except LookupError:
        return w
    return w


def _tag_pos(tokens: list[str]) -> list[tuple[str, str, str]]:
    """NLTK POS tag and lemmatize. Returns [(word, lemma, simple_pos)]."""
    tagged = pos_tag(tokens)
    results = []
    for word, ptb_tag in tagged:
        lemma = lemmatize(word)
        simple_pos = PTB_TO_SIMPLE.get(ptb_tag, 'other')
        results.append((word, lemma, simple_pos))
    return results


class WordAnalyzer:
    def __init__(self):
        self.stop_words = STOP_WORDS
        self.momo_vocab = MOMO_VOCAB

    def tokenize_and_tag(self, text: str) -> list[dict]:
        """Tokenize English text with POS tagging.

        Returns list of {word, lemma, pos} dicts.
        """
        sentences = []
        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue
            denom = max(len(re.sub(r'\s', '', line)), 1)
            en_ratio = len(re.findall(r'[a-zA-Z]', line)) / denom
            if en_ratio > 0.3:
                sentences.append(line)

        results = []
        for sentence in sentences:
            try:
                tokens = word_tokenize(sentence)
            except Exception:
                tokens = re.findall(r'\b[a-zA-Z]+\b', sentence)

            english_tokens = [t for t in tokens if re.match(r'^[a-zA-Z]+$', t) and len(t) >= 2]
            if not english_tokens:
                continue

            for word, lemma, pos in _tag_pos(english_tokens):
                wl = word.lower()
                if 'answersheet' in wl or ('answer' in wl and 'sheet' in wl):
                    continue
                if len(wl) > 28:
                    continue
                if word.lower() in self.stop_words:
                    continue
                if lemma.lower() in self.stop_words:
                    continue
                if len(lemma) < 2:
                    continue
                results.append({'word': word, 'lemma': lemma, 'pos': pos})

        return results

    def build_frequency_index(self, papers: list[dict]) -> dict:
        """Build frequency index with (year, section, pos) triplet dedup.

        Args:
            papers: [{year, section, section_label, sentences: [str]}]

        Returns:
            {lemma: {lemma, variants, senses, pos_counts, pos_units,
                      sentences_by_pos, frequency}}
        """
        all_units = set((p['year'], p['section']) for p in papers)
        total_units = len(all_units)

        word_index = defaultdict(lambda: {
            'lemma': '',
            'variants': set(),
            'pos_counts': defaultdict(int),
            'pos_units': defaultdict(set),
            'sentences_by_pos': defaultdict(list),
        })

        for paper in papers:
            year = paper['year']
            section = paper['section']
            section_label = paper.get('section_label', section)
            from src.backend.section_splitter import clean_exam_sentences
            content_sentences = clean_exam_sentences(paper.get('sentences', []))
            text = '\n'.join(content_sentences)
            tokens = self.tokenize_and_tag(text)

            seen_pairs = set()

            for t in tokens:
                lemma = t['lemma']
                pos = t['pos']
                word = t['word']

                info = word_index[lemma]
                info['lemma'] = lemma
                info['variants'].add(word.lower())

                pair = (lemma, year, section, pos)
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    info['pos_units'][pos].add((year, section))

            # Collect sentences — split paragraphs into actual sentences
            from nltk.tokenize import sent_tokenize
            for sentence_text in content_sentences:
                # Split paragraph into individual sentences
                try:
                    sents = sent_tokenize(sentence_text)
                except Exception:
                    sents = [sentence_text]
                for sent in sents:
                    sent_lower = sent.lower()
                    for t in tokens:
                        lemma = t['lemma']
                        word = t['word']
                        pos = t['pos']
                        wl = word.lower()
                        # Whole-word match (not substring: "art" should not match "part")
                        if re.search(r'\b' + re.escape(wl) + r'\b', sent_lower):
                            existing = word_index[lemma]['sentences_by_pos'][pos]
                            if not any(s['text'] == sent for s in existing):
                                existing.append({
                                    'year': year,
                                    'section': section,
                                    'section_label': section_label,
                                    'text': sent,
                                    'word': wl,
                                })

        # Finalize
        for lemma in word_index:
            info = word_index[lemma]
            info['variants'] = list(info['variants'])
            info['pos_units'] = {k: list(v) for k, v in info['pos_units'].items()}
            info['pos_counts'] = {pos: len(units) for pos, units in info['pos_units'].items()}
            info['sentences_by_pos'] = dict(info['sentences_by_pos'])

            # Populate senses and examples from 墨墨 vocab
            info['senses'] = []
            momo_entry = self.momo_vocab.get(lemma, {})
            momo_senses = momo_entry.get('senses', [])
            info['momo_examples'] = momo_entry.get('examples_en', [])
            for s in momo_senses:
                pos = s['pos']
                cnt = info['pos_counts'].get(pos, 0)
                if cnt > 0:  # Only show senses with actual occurrences
                    info['senses'].append({
                        'pos': pos,
                        'meaning': s['meaning'],
                        'count': cnt,
                    })

            # If no momo senses, create from discovered POS
            if not info['senses']:
                for pos in sorted(info['pos_counts'].keys()):
                    info['senses'].append({
                        'pos': pos,
                        'meaning': '',
                        'count': info['pos_counts'][pos],
                    })

            # Word-level frequency (union of all POS unit sets)
            union_units = set()
            for units in info['pos_units'].values():
                union_units.update(units)
            info['frequency'] = len(union_units) / total_units if total_units > 0 else 0

        return dict(word_index)


def classify_by_frequency(word_index: dict, high_threshold: float = 0.5,
                          medium_threshold: float = 0.2) -> dict[str, list]:
    """Classify words into high/medium/low frequency bands."""
    bands = {'high': [], 'medium': [], 'low': []}
    for lemma, info in word_index.items():
        freq = info.get('frequency', 0)
        if freq >= high_threshold:
            bands['high'].append(lemma)
        elif freq >= medium_threshold:
            bands['medium'].append(lemma)
        else:
            bands['low'].append(lemma)
    return bands


def load_word_list(path: str) -> set[str]:
    """Load a plain text word list (one word per line)."""
    words = set()
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                w = line.strip().lower()
                if w:
                    words.add(w)
    except Exception:
        pass
    return words


def apply_basic_word_filter(word_index: dict, exclude: set[str]) -> dict:
    """Remove excluded words from the index."""
    return {k: v for k, v in word_index.items() if k not in exclude}
