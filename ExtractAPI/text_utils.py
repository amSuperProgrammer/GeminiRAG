import re
from typing import List
from PyPDF2 import PdfReader
import docx

def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def extract_text_from_docx(file_path: str) -> str:
    doc = docx.Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)

def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)  # убрать лишние пробелы/переносы
    return text.strip()

def chunk_text(text: str, chunk_size: int = 800) -> List[str]:
    words = text.split()
    chunks = []
    current = []

    for w in words:
        current.append(w)
        if len(current) >= chunk_size:
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))

    return chunks