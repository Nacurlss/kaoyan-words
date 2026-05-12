import re
import subprocess
import docx
import pdfplumber
from pathlib import Path


def parse_docx(file_path: str) -> str:
    """Extract all text from a .docx/.docm file. Falls back to textutil."""
    try:
        doc = docx.Document(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs)
        if text.strip():
            return text
    except Exception:
        pass
    return parse_doc(file_path)


def parse_doc(file_path: str) -> str:
    """Extract text from .doc using macOS textutil."""
    result = subprocess.run(
        ['textutil', '-convert', 'txt', '-stdout', str(file_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"textutil failed: {result.stderr}")
    return result.stdout


def parse_pdf(file_path: str) -> str:
    """Extract all text from a .pdf file."""
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def parse_file(file_path: str) -> str:
    """Parse a doc/docx/pdf file and return extracted text."""
    ext = Path(file_path).suffix.lower()
    if ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".doc":
        return parse_doc(file_path)
    elif ext == ".pdf":
        return parse_pdf(file_path)
    raise ValueError(f"Unsupported file format: {ext}")


def extract_english_sentences(text: str) -> list[dict]:
    """
    Extract English sentences with their context.
    Returns list of dicts: {sentence, year_hint}
    """
    # Split text into blocks, extract ones that contain English words
    lines = text.split("\n")
    sentences = []
    current_sentence = ""

    for line in lines:
        line = line.strip()
        if not line:
            if current_sentence:
                # Check if the sentence has enough English content
                english_ratio = _english_char_ratio(current_sentence)
                if english_ratio > 0.3:
                    sentences.append({"sentence": current_sentence.strip()})
                current_sentence = ""
            continue

        # Heuristic: if line looks like a header/number, skip
        if re.match(r'^[\d一二三四五六七八九十]+[\.\、\s]', line):
            if current_sentence:
                english_ratio = _english_char_ratio(current_sentence)
                if english_ratio > 0.3:
                    sentences.append({"sentence": current_sentence.strip()})
                current_sentence = ""
            current_sentence = line
        else:
            if current_sentence:
                current_sentence += " " + line
            else:
                current_sentence = line

    if current_sentence:
        english_ratio = _english_char_ratio(current_sentence)
        if english_ratio > 0.3:
            sentences.append({"sentence": current_sentence.strip()})

    return sentences


def _english_char_ratio(text: str) -> float:
    """Calculate ratio of English characters in text."""
    if not text:
        return 0
    english_chars = len(re.findall(r'[a-zA-Z]', text))
    total_chars = len(re.sub(r'\s', '', text))
    if total_chars == 0:
        return 0
    return english_chars / total_chars


def extract_year_from_filename(filename: str) -> str:
    """Extract year from filename like '2010年考研英语一真题.pdf'."""
    match = re.search(r'(\d{4})', filename)
    if match:
        return match.group(1)
    return "unknown"
