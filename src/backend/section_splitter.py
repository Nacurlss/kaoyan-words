#!/usr/bin/env python3
"""Split 考研英语 exams (PDF/DOCX) into sections by question type.

Supports 1986-2025, handling:
  - Standard: Section I/II/III/IV with Use of English / Reading / Writing / Translation
  - Early years: Part I/II/III, Close Test, Passage 1-5
  - Unicode Roman numerals (ⅠⅡⅢⅣⅤ) and no-space variants (SectionⅠUseofEnglish)
  - DOCX multi-year bundles (split by year, then by section)
"""

import re
from dataclasses import dataclass, field


# ── Regex patterns ──
# Section header: "Section I Use of English" / "SectionⅠUseofEnglish" etc
SECTION_RE = re.compile(
    r'(?:Section|SECTION)\s*([IVXⅠⅡⅢⅣⅤⅥvii]+)\s*(.*)', re.IGNORECASE
)
PART_RE = re.compile(r'^Part\s*([ABCabc])\b')
# Year boundary in DOCX bundles: "1995年全国硕士研究生入学统一考试英语试题"
YEAR_RE = re.compile(r'(19|20)(\d{2})年.*(?:研究生|硕士).*(?:英语|英文)')
# Translation sentence markers
TRANS_MARKER_RE = re.compile(r'\(?(4[6-9]|50)\)?')
# Answer-choice line: "[A] word [B] word [C] word [D] word"
# Use full-width bracket variants too
CHOICE_LINE_RE = re.compile(r'[\[［（(]?[A-EＡ-Ｅ][\]］）)、\.\s].+[\[［（(]?[A-EＡ-Ｅ][\]］）)、\.\s].+[\[［（(]?[A-EＡ-Ｅ][\]］）)、\.\s]', re.IGNORECASE)
OPTION_BLOCK_RE = re.compile(
    r'(?:^|\s)(?:\d{1,2}[\.\)]\s*)?[\[［（(]?[A-EＡ-Ｅ][\]］）)、\.\s]',
    re.IGNORECASE,
)
NUMBERED_OPTION_START_RE = re.compile(
    r'\s+\d{1,2}[\.\)]\s*[\[［（(]?[A-EＡ-Ｅ][\]］）)、\.\s]',
    re.IGNORECASE,
)
QUESTION_START_RE = re.compile(
    r'^(?:\d{1,2}[\.\)]\s*)?('
    r'which of the following|according to (the|paragraph)|the author|'
    r'what (can|does|is|will|would|the|may|might|could|should|are|do|was|were|did|has|have)|'
    r'why (does|is|are|do|would|might|can|could)|'
    r'how (does|is|can|would|could|might|should|do)|'
    r'it can be inferred|we can infer|we can learn|the word|the phrase|'
    r'the passage|this text|from the text|paragraph \d+|'
    r'in the first paragraph|in the second paragraph|in the third paragraph|'
    r'in the last paragraph|in paragraph|in the opening paragraph|'
    r'by (saying|citing|referring|mentioning)|'
    r'the text (suggests|indicates|shows|implies|discusses)|'
    r'the most appropriate|the best title|the main idea|'
    r'all of the following|judging from|in the context|'
    r'to (which|what|whom)'
    r')\b',
    re.IGNORECASE,
)
QUESTION_HINT_RE = re.compile(
    r'(as mentioned in the passage|according to the passage|'
    r'can best be described|is most likely to|are most likely to|'
    r'the author (suggests|indicates|believes|argues|intends|implies|mentions|'
    r'attitude|feels|states|concludes|notes|discusses|claims|maintains|views)|'
    r'the passage (suggests|indicates|implies)|'
    r'we can infer from|we can learn from|'
    r'referred to as|is used to|is mentioned to|'
    r'the underlined|refers to|'
    r'it can be|we can|it is indicated|it is implied|'
    r'may best be|might best be|can be concluded|can be inferred)',
    re.IGNORECASE,
)
INSTRUCTION_RE = re.compile(
    r'(directions|answer sheet|choose the best|mark your answer|mark your answers|'
    r'read the following|answer the questions|write (an essay|a letter|a short|a composition|your essay)|'
    r'you should write|your composition|word limit|do not sign|do not write|'
    r'your translation|translate the following|study the following|'
    r'考生注意|注意事项|考生须知|启用前|绝密|科目代码|'
    r'全国硕士|研究生招生|入学统一考试|'
    r'考试时间|满分|考试结束|答题卡|'
    r'选择题的答案|非选择题的答案|填[（(]书[）)]写|'
    r'试卷条形码|考生编号|报考单位|'
    r'黑色字迹|签字笔|2B铅笔|'
    r'草稿纸|试题册|按规定交回)',
    re.IGNORECASE,
)
QUESTION_ONLY_LINE_RE = re.compile(
    r'^(?:\d{1,2}[\.\)、]\s*)?'
    r'(?:'
    r'[A-Z][a-zA-Z].{5,80}[\?？]|'
    r'[A-Z][a-zA-Z].{5,180}\b(because|suggests|refers to|indicates|implies|shows|discusses|'
    r'according|main idea|best title|most appropriate|mainly about|mainly discusses|'
    r'NOT true|is true|is mentioned|is NOT|can be|can we|intends to|aims to|'
    r'the author|we can learn|we can infer|it can be|what can|what is|what does|'
    r'what would|what could|what are|how does|why does|'
    r'may best|might best|can be concluded|can be inferred|'
    r'the following|all of|which of|the most|judging from|in the context|'
    r'none of|according to|to which)'
    r'.{0,80}$|'
    r'[A-Z][a-zA-Z].{5,200}_{3,}\s*$'  # Lines ending with blanks
    r')',
    re.IGNORECASE,
)
OPTION_ONLY_LINE_RE = re.compile(
    r'^[A-E][\.\)\s、]\s*.{3,200}$'
)
BULLET_LINE_RE = re.compile(
    r'^[•·\-\*‏]\s+[A-Za-z].{5,200}$'
)
UNICODE_CTRL_RE = re.compile(r'[\u200b\u200e\u200f\u202a\u202b\u202c\u202d\u202e\ufeff]')
NUMBERED_QUESTION_RE = re.compile(
    r'^\d{1,2}[\.\)、]\s*[A-Z][a-z].{8,200}$'
)
CHINESE_METADATA_RE = re.compile(
    r'^(?:绝密|启用前|全国硕士|研究生招生|'
    r'英语[（(][一二][）)]|科目代码|'
    r'考生注意|注意事项|考生须知|'
    r'答题前|考试时间|满分|考试结束|'
    r'以下信息|考生编号|报考单位|'
    r'试卷条形码|黑色字迹|签字笔|草稿纸|试题册)',
)


@dataclass
class Section:
    key: str
    label: str
    label_en: str
    pages: list[str] = field(default_factory=list)
    sentences: list[str] = field(default_factory=list)


# ── Helpers ──

def _en_ratio(text: str) -> float:
    if not text:
        return 0
    en = len(re.findall(r'[a-zA-Z]', text))
    total = len(re.sub(r'\s', '', text))
    return en / total if total > 0 else 0


def _zh_ratio(text: str) -> float:
    if not text:
        return 0
    zh = len(re.findall(r'[一-鿿]', text))
    total = len(re.sub(r'\s', '', text))
    return zh / total if total > 0 else 0


def _rejoin_hyphenated(text: str) -> str:
    """Re-join words split by PDF soft line breaks.

    Patterns:
      - "air-\nports" or "air-\n  ports" → "airports"
      - "(\w+) \n(\w+)" where line below starts lowercase → rejoin
    """
    # Hyphenated line break: "word-\nword"
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    # Soft line break within a word: "\n" followed by lowercase-only word
    text = re.sub(r'\n\s*([a-z]{2,})\s*\n', r'\1\n', text)
    return text


def _mark_translation_sentences(text: str) -> str:
    """Wrap translation sentences in [[...]] markers.

    Detects (46) through (50) markers and wraps content until
    next marker or double-newline.
    """
    lines = text.split('\n')
    result = []
    in_trans = False
    trans_buf = []

    for line in lines:
        m = TRANS_MARKER_RE.search(line)
        if m:
            if in_trans:
                # Close previous translation segment
                result.append('[[' + ' '.join(trans_buf) + ']]')
                trans_buf = []
            in_trans = True
            # Keep the marker + rest of line
            trans_buf.append(line.strip())
        elif in_trans:
            # Check if we've hit a blank line or new section
            stripped = line.strip()
            if not stripped:
                result.append('[[' + ' '.join(trans_buf) + ']]')
                trans_buf = []
                in_trans = False
                result.append('')
            elif _en_ratio(stripped) < 0.1 and _zh_ratio(stripped) > 0.3:
                # Chinese-only line after translation → close segment
                result.append('[[' + ' '.join(trans_buf) + ']]')
                trans_buf = []
                in_trans = False
                result.append(line)
            else:
                trans_buf.append(stripped)
        else:
            result.append(line)

    if in_trans and trans_buf:
        result.append('[[' + ' '.join(trans_buf) + ']]')

    return '\n'.join(result)


def _clean_content_paragraph(text: str) -> str | None:
    """Keep article content and drop exam instructions, questions, and options."""
    text = UNICODE_CTRL_RE.sub('', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('[[', '').replace(']]', '').strip()
    if not text:
        return None

    # Skip Chinese metadata
    if CHINESE_METADATA_RE.match(text):
        return None

    # Skip pure instructions/headers
    if INSTRUCTION_RE.search(text) and _en_ratio(text) < 0.6:
        return None

    text = re.sub(r'^Directions[:：]?\s*', '', text, flags=re.IGNORECASE).strip()
    if not text:
        return None

    if re.match(r'^(Section|Part|Text|Passage)\s*[A-Z\dⅠⅡⅢⅣⅤ]*\b', text, re.IGNORECASE):
        return None

    # Cloze paragraphs sometimes glue instructions + passage + all options.
    # Keep the passage after "(10 points)" or similar markers.
    if INSTRUCTION_RE.search(text):
        m = re.search(r'\(?\[?\s*(?:10|15|20)\s+points\s*\]?\)?[\.\s]*(.+)$', text, re.IGNORECASE)
        if m and len(m.group(1).strip()) > 30:
            text = m.group(1).strip()
        else:
            if len(text) > 300 and _en_ratio(text) > 0.5:
                pass
            else:
                return None

    # Cut off numbered options at the end (e.g., "21. [A] text [B] text")
    option_suffix = NUMBERED_OPTION_START_RE.search(text)
    if option_suffix:
        text = text[:option_suffix.start()].strip()

    # Cut off unnumbered [A] or ［A］ patterns in the latter half
    unumbered_option = re.search(r'\s+[\[［（(][A-EＡ-Ｅ][\]］）)、\.\s]', text)
    if unumbered_option and unumbered_option.start() > len(text) * 0.5:
        text = text[:unumbered_option.start()].strip()

    # Cut off question segments glued to end of article paragraphs
    # Pattern: legitimate article text ends, then a question starts with typical patterns
    question_cut = QUESTION_START_RE.search(text)
    if question_cut and question_cut.start() > len(text) * 0.3:
        text = text[:question_cut.start()].strip()

    if not text:
        return None

    # If the paragraph ends with options like [A]...[B]..., cut them
    m_choice = CHOICE_LINE_RE.search(text)
    if m_choice and m_choice.start() > len(text) * 0.4:
        text = text[:m_choice.start()].strip()

    if not text:
        return None

    option_count = len(OPTION_BLOCK_RE.findall(text))
    if option_count >= 3:
        if len(text) < 500:
            return None

    if OPTION_BLOCK_RE.match(text):
        return None

    if QUESTION_START_RE.match(text):
        return None

    if QUESTION_HINT_RE.search(text) and len(text) < 180:
        return None

    if _en_ratio(text) <= 0.15:
        return None

    return text


def clean_exam_sentences(sentences: list[str]) -> list[str]:
    """Clean pre-split exam paragraphs before vocabulary analysis."""
    cleaned: list[str] = []
    for sentence in sentences:
        item = _clean_content_paragraph(sentence)
        if item:
            cleaned.append(item)
    return cleaned


def _extract_sentences(text: str) -> list[str]:
    """Extract content paragraphs preserving structure.

    Unlike v1 which collapsed everything, this version:
      - Preserves paragraph breaks (blank lines → separate entries)
      - Fixes PDF soft line breaks within paragraphs
      - Marks translation sentences with [[...]]
      - Keeps section headers ("Directions:", "Text 1") as their own entries
      - Filters out answer-choice rows
    """
    text = _rejoin_hyphenated(text)
    text = _mark_translation_sentences(text)

    lines = text.split('\n')
    paragraphs = []
    current: list[str] = []

    def flush():
        nonlocal current
        if not current:
            return
        joined = ' '.join(current).strip()
        cleaned = _clean_content_paragraph(joined)
        if cleaned:
            paragraphs.append(cleaned)
        current = []

    for line in lines:
        stripped = line.strip()
        stripped = UNICODE_CTRL_RE.sub('', stripped)

        # Blank line → paragraph boundary
        if not stripped:
            flush()
            continue

        # Skip Chinese metadata lines (exam header info)
        if CHINESE_METADATA_RE.match(stripped):
            flush()
            continue

        # Skip purely Chinese content
        if _en_ratio(stripped) < 0.05:
            flush()
            continue

        # Skip question-only lines (numbered comprehension questions)
        if QUESTION_ONLY_LINE_RE.match(stripped):
            flush()
            continue

        # Skip numbered question lines (e.g., "14. What the author tries to...")
        if NUMBERED_QUESTION_RE.match(stripped):
            flush()
            continue

        # Skip bullet-point option lines (e.g., "• promote cooperation...")
        if BULLET_LINE_RE.match(stripped):
            flush()
            continue

        # Skip answer-choice-only lines with [A] or A. patterns
        if CHOICE_LINE_RE.match(stripped):
            flush()
            continue

        # Skip single option lines (A. text)
        if OPTION_ONLY_LINE_RE.match(stripped):
            flush()
            continue

        # Headers/instructions are not article content.
        if re.match(r'^(Directions|Section|Part|Text\s*\d|Passage\s*\d)', stripped, re.IGNORECASE):
            flush()
            continue

        # Translation marker lines → always start new paragraph
        if TRANS_MARKER_RE.search(stripped) or '[[' in stripped:
            flush()
            cleaned = _clean_content_paragraph(stripped)
            if cleaned:
                paragraphs.append(cleaned)
            continue

        current.append(stripped)

    flush()
    return paragraphs


# ── Section detection (text-based, works on PDF and DOCX) ──

def _detect_section_type(normalized: str, line_lower: str) -> str | None:
    """Return section key from a detected section header line, or None."""
    # Use of English / Cloze / Close Test
    if any(kw in normalized for kw in [
        'useofenglish', 'usenglish', 'clozetest', 'closetest',
        'iusenglish', 'iuseofenglish', 'sectionⅰuseofenglish',
    ]):
        return 'use_of_english'

    # Reading Comprehension
    if any(kw in normalized for kw in [
        'readingcomprehension', 'iireading', 'ⅱreading',
        'sectionⅱreading', 'sectioniireading',
    ]):
        return 'reading_a'

    # Translation (standalone section)
    if any(kw in normalized for kw in [
        'translation', 'iiitranslation', 'ⅲtranslation',
        'english-chinese', 'englishchinese',
    ]):
        return 'reading_c'

    # Writing
    if any(kw in normalized for kw in [
        'writing', 'iiiwriting', 'ivwriting', 'ⅲwriting', 'sectionwriting',
    ]):
        return 'writing_a'

    return None


def _split_text(all_text: str) -> list[Section]:
    """Split text by section/part boundaries. Works on PDF or DOCX text."""
    sections: list[Section] = []
    current_key = ""
    current_label = ""
    current_label_en = ""
    buffer: list[str] = []

    def flush():
        nonlocal buffer
        if not current_key:
            return
        text = '\n'.join(buffer)
        parsed = _extract_sentences(text)
        if parsed:
            sections.append(Section(
                key=current_key, label=current_label,
                label_en=current_label_en,
                pages=[text], sentences=parsed,
            ))
        buffer = []

    # Detect reading Part B/C from context within reading section
    READING_PART_B_MARKERS = ['partb', 'part b', 'readingb', 'section b',
                               '七选五', '排序', '选择搭配', '新题型']
    READING_PART_C_MARKERS = ['partc', 'part c', 'readingc', 'translation',
                               '翻译', '英译汉']

    lines = all_text.split('\n')

    for line in lines:
        line_s = line.strip()
        lower = line_s.lower()
        normalized = re.sub(r'\s+', '', lower)

        # ── Section header detection ──
        has_section_word = 'section' in normalized or 'part' in normalized
        section_type = _detect_section_type(normalized, lower) if has_section_word else None

        if section_type:
            flush()
            current_key = section_type
            if section_type == 'use_of_english':
                current_label = '完形填空'
                current_label_en = 'Use of English'
            elif section_type == 'reading_a':
                current_label = '阅读理解A'
                current_label_en = 'Reading Comprehension Part A'
            elif section_type == 'reading_c':
                current_label = '阅读理解C（翻译）'
                current_label_en = 'Translation'
            elif section_type == 'writing_a':
                current_label = '写作A（应用文）'
                current_label_en = 'Writing Part A'
            buffer = []
            continue

        # ── Part B/C within reading/writing ──
        pm = PART_RE.match(line_s)
        if pm:
            part = pm.group(1).upper()
            is_writing_ctx = 'writing' in current_key

            if part == 'A':
                flush()
                if is_writing_ctx:
                    current_key = 'writing_a'
                    current_label = '写作A（应用文）'
                    current_label_en = 'Writing Part A'
                else:
                    current_key = 'reading_a'
                    current_label = '阅读理解A'
                    current_label_en = 'Reading Comprehension Part A'
                buffer = []

            elif part == 'B':
                flush()
                if is_writing_ctx:
                    current_key = 'writing_b'
                    current_label = '写作B（大作文）'
                    current_label_en = 'Writing Part B'
                else:
                    current_key = 'reading_b'
                    current_label = '阅读理解B'
                    current_label_en = 'Reading Comprehension Part B'
                buffer = []

            elif part == 'C':
                flush()
                current_key = 'reading_c'
                current_label = '阅读理解C（翻译）'
                current_label_en = 'Reading Comprehension Part C'
                buffer = []

            continue

        # ── Content ──
        if current_key:
            buffer.append(line)

    flush()
    return sections


# ── Public API ──

def split_text(text: str) -> list[Section]:
    """Split any text (from PDF or DOCX) into sections."""
    return _split_text(text)


def split_pdf(pdf_path: str) -> list[Section]:
    """Split a single-year exam PDF into sections."""
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"
    return _split_text(all_text)


def split_docx_by_year(docx_path: str) -> list[tuple[str, str]]:
    """Split a multi-year DOCX bundle into [(year, full_text), ...].

    Reads both paragraphs and tables, detects year boundaries,
    and returns per-year text blocks.
    """
    import docx as dx

    doc = dx.Document(docx_path)
    all_lines: list[str] = []

    # Read paragraphs
    for p in doc.paragraphs:
        all_lines.append(p.text)

    # Read tables (options often in tables for early years)
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_texts:
                all_lines.append(' '.join(row_texts))

    full_text = '\n'.join(all_lines)

    # Split by year boundaries
    year_blocks: list[tuple[str, str]] = []
    current_year = None
    current_lines: list[str] = []

    for line in all_lines:
        ym = YEAR_RE.search(line)
        if ym:
            # Flush previous year
            if current_year and current_lines:
                year_blocks.append((current_year, '\n'.join(current_lines)))
            current_year = f"{ym.group(1)}{ym.group(2)}"
            current_lines = [line]
        elif current_year:
            current_lines.append(line)

    if current_year and current_lines:
        year_blocks.append((current_year, '\n'.join(current_lines)))

    return year_blocks


def detect_exam_type(text_or_path: str) -> str:
    """Detect 英语一 or 英语二 from text or PDF path."""
    if text_or_path.endswith('.pdf'):
        import pdfplumber
        with pdfplumber.open(text_or_path) as pdf:
            for page in pdf.pages[:2]:
                t = page.extract_text()
                if t:
                    if '英语（一）' in t or '英语一' in t:
                        return '英语一'
                    if '英语（二）' in t or '英语二' in t:
                        return '英语二'
    else:
        if '英语（一）' in text_or_path or '英语一' in text_or_path:
            return '英语一'
        if '英语（二）' in text_or_path or '英语二' in text_or_path:
            return '英语二'
    return '未知'


def extract_year_from_filename(filename: str) -> str:
    match = re.search(r'(\d{4})', filename)
    return match.group(1) if match else 'unknown'
