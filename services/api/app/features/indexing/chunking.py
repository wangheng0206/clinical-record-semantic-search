"""Split clinical document bodies into embedding-sized chunks.

Sizing rationale: the embedding service accepts at most 256 tokens and
8,000 characters per text. English clinical prose averages ~4 characters
per token, so a 1,000-character packing target keeps every chunk inside
the token limit and far below the character hard limit.
"""

from __future__ import annotations

import hashlib
import re

TARGET_CHUNK_CHARS = 1_000
OVERLAP_CHARS = 150
HARD_MAX_CHARS = 8_000

_BLANK_LINE = re.compile(r"\n\s*\n+")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def content_hash(title: str, body: str) -> str:
    """Stable hash of the searchable source content (title + body)."""
    normalized = f"{title.strip()}\n{body.strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _split_oversized(paragraph: str, target_chars: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_END.split(paragraph):
        candidate = f"{current} {sentence}" if current else sentence
        if current and len(candidate) > target_chars:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
        while len(current) > target_chars:
            pieces.append(current[:target_chars])
            current = current[target_chars:]
    if current:
        pieces.append(current)
    return pieces


def chunk_document(
    body: str,
    *,
    target_chars: int = TARGET_CHUNK_CHARS,
    overlap_chars: int = OVERLAP_CHARS,
) -> list[str]:
    """Split *body* into overlapping chunks. Blank input yields no chunks."""
    text = body.strip()
    if not text:
        return []

    pieces: list[str] = []
    for paragraph in _BLANK_LINE.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= target_chars:
            pieces.append(paragraph)
        else:
            pieces.extend(_split_oversized(paragraph, target_chars))

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if current and len(candidate) > target_chars:
            chunks.append(current)
            tail = current[-overlap_chars:].lstrip()
            current = f"{tail}\n\n{piece}" if tail else piece
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks
