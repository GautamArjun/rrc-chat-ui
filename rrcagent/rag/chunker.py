"""Document chunker for the RAG pipeline.

Loads .md, .txt, and .docx files and splits them into Chunk objects
using paragraph-based splitting with configurable max chunk size.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    source: str
    chunk_index: int
    study_id: str
    embedding: list[float] | None = None


def load_and_chunk(
    file_path: str,
    study_id: str,
    max_chunk_size: int = 1000,
) -> list[Chunk]:
    """Load a document and split it into chunks.

    Args:
        file_path: Path to .md, .txt, or .docx file.
        study_id: Study identifier to tag each chunk with.
        max_chunk_size: Maximum character length per chunk.

    Returns:
        List of Chunk objects with text and metadata.

    Raises:
        ValueError: If the file type is not supported.
    """
    ext = os.path.splitext(file_path)[1].lower()
    source = os.path.basename(file_path)

    if ext == ".md":
        paragraphs = _load_text(file_path)
    elif ext == ".txt":
        paragraphs = _load_text(file_path)
    elif ext == ".docx":
        paragraphs = _load_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    # Filter empty paragraphs
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    # For markdown with section-aware splitting, each section is already
    # a semantic unit — only split further if a section exceeds max_chunk_size
    if ext == ".md" and any("\n## " in p or p.startswith("## ") for p in paragraphs):
        raw_chunks = []
        for para in paragraphs:
            if len(para) > max_chunk_size:
                raw_chunks.extend(_split_long_text(para, max_chunk_size))
            else:
                raw_chunks.append(para)
    else:
        # Group paragraphs into chunks respecting max_chunk_size
        raw_chunks = _split_into_chunks(paragraphs, max_chunk_size)

    return [
        Chunk(text=text, source=source, chunk_index=i, study_id=study_id)
        for i, text in enumerate(raw_chunks)
    ]


def _load_text(file_path: str) -> list[str]:
    """Load a plain text or markdown file and split into paragraphs.

    For markdown files, splits by ## section headers so each Q&A stays
    together as one paragraph. For plain text, splits by double newlines.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if file_path.endswith(".md") and "\n## " in content:
        return _split_markdown_sections(content)

    return content.split("\n\n")


def _split_markdown_sections(content: str) -> list[str]:
    """Split markdown content by ## headers, keeping header + body together."""
    import re
    sections = re.split(r"\n(?=## )", content)
    result = []
    for section in sections:
        text = section.strip()
        if not text:
            continue
        # Skip the top-level heading if it's alone (e.g., "# ZYN Study FAQ")
        if text.startswith("# ") and "\n## " not in text and "\n" not in text.strip():
            continue
        # If this section starts with a top-level heading followed by ##,
        # strip the top-level heading
        if text.startswith("# ") and "\n## " in text:
            idx = text.index("\n## ")
            top_heading = text[:idx].strip()
            rest = text[idx:].strip()
            # Re-split the rest by ## headers
            sub_sections = re.split(r"\n(?=## )", rest)
            for sub in sub_sections:
                sub = sub.strip()
                if sub:
                    result.append(sub)
            continue
        result.append(text)
    return result


def _load_docx(file_path: str) -> list[str]:
    """Load a .docx file and extract paragraph text."""
    from docx import Document

    doc = Document(file_path)
    return [p.text for p in doc.paragraphs]


def _split_into_chunks(paragraphs: list[str], max_size: int) -> list[str]:
    """Group paragraphs into chunks, splitting long ones if needed."""
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        # If adding this paragraph exceeds max, flush current
        if current and len(current) + len(para) + 1 > max_size:
            chunks.append(current.strip())
            current = ""

        # If the paragraph itself exceeds max, split it by sentences
        if len(para) > max_size:
            if current:
                chunks.append(current.strip())
                current = ""
            for part in _split_long_text(para, max_size):
                chunks.append(part.strip())
        else:
            current = current + "\n" + para if current else para

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _split_long_text(text: str, max_size: int) -> list[str]:
    """Split a long text into pieces at word boundaries."""
    words = text.split()
    parts: list[str] = []
    current = ""

    for word in words:
        if current and len(current) + len(word) + 1 > max_size:
            parts.append(current)
            current = word
        else:
            current = current + " " + word if current else word

    if current:
        parts.append(current)

    return parts
