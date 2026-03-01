"""
Document Processor for AZAN — Phase 3
Accepts PDF and Markdown files, extracts text, chunks it,
and indexes into ChromaDB for RAG retrieval.
"""

import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    try:
        from PyPDF2 import PdfReader
        import io
        reader = PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        return "\n\n".join(pages)
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return ""


def _extract_text_from_markdown(file_bytes: bytes) -> str:
    """Extract plain text from Markdown bytes (strip formatting)."""
    text = file_bytes.decode("utf-8", errors="replace")
    # Strip images, links markup, headers markers
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"(\*{1,2}|_{1,2})(.*?)\1", r"\2", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    return text.strip()


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks of ~chunk_size characters."""
    if not text:
        return []
    words = text.split()
    chunks = []
    current: List[str] = []
    current_len = 0

    for word in words:
        current.append(word)
        current_len += len(word) + 1
        if current_len >= chunk_size:
            chunks.append(" ".join(current))
            # Keep last `overlap` chars worth of words for context continuity
            overlap_words = []
            overlap_len = 0
            for w in reversed(current):
                if overlap_len + len(w) > overlap:
                    break
                overlap_words.insert(0, w)
                overlap_len += len(w) + 1
            current = overlap_words
            current_len = overlap_len

    if current:
        chunks.append(" ".join(current))

    return chunks


def process_document(filename: str, file_bytes: bytes) -> Dict:
    """
    Process an uploaded document: extract text, chunk, and index to ChromaDB.

    Args:
        filename: Original filename (used to detect type)
        file_bytes: Raw bytes of the file

    Returns:
        Dict with processing results
    """
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        text = _extract_text_from_pdf(file_bytes)
    elif ext in (".md", ".markdown", ".txt"):
        text = _extract_text_from_markdown(file_bytes)
    else:
        return {"success": False, "error": f"Unsupported file type: {ext}"}

    if not text or len(text) < 20:
        return {"success": False, "error": "Could not extract meaningful text from document"}

    chunks = _chunk_text(text)
    if not chunks:
        return {"success": False, "error": "Text chunking produced no results"}

    # Save file locally
    save_path = UPLOAD_DIR / filename
    save_path.write_bytes(file_bytes)

    # Index chunks into ChromaDB
    from src.semantic_search import get_vector_store
    vs = get_vector_store()
    indexed = 0
    failed = 0
    doc_id_base = hashlib.md5(filename.encode()).hexdigest()[:12]

    for i, chunk in enumerate(chunks):
        chunk_id = f"doc_{doc_id_base}_{i}"
        article = {
            "id": chunk_id,
            "headline": f"{filename} (chunk {i+1}/{len(chunks)})",
            "body": chunk,
            "source": f"upload:{filename}",
            "category": "document",
            "published_at": "uploaded",
        }
        if vs.add_article(article):
            indexed += 1
        else:
            failed += 1

    logger.info(f"✓ Processed '{filename}': {len(chunks)} chunks, {indexed} indexed")

    return {
        "success": True,
        "filename": filename,
        "text_length": len(text),
        "chunks": len(chunks),
        "indexed": indexed,
        "failed": failed,
    }


def get_document_stats() -> Dict:
    """Return stats about processed documents."""
    files = list(UPLOAD_DIR.glob("*"))
    return {
        "total_documents": len(files),
        "filenames": [f.name for f in files],
    }
