from app.features.indexing.chunking import (
    HARD_MAX_CHARS,
    OVERLAP_CHARS,
    TARGET_CHUNK_CHARS,
    chunk_document,
    content_hash,
)

CHUNK_CEILING = TARGET_CHUNK_CHARS + OVERLAP_CHARS + 2


def test_paragraphs_are_packed_up_to_the_target() -> None:
    paragraphs = [f"Paragraph {index} " + "x" * 400 for index in range(4)]
    chunks = chunk_document("\n\n".join(paragraphs))
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= CHUNK_CEILING
        assert len(chunk) <= HARD_MAX_CHARS


def test_blank_body_produces_no_chunks() -> None:
    assert chunk_document("   \n\t \n") == []


def test_oversized_paragraph_is_split_without_losing_order() -> None:
    sentences = [f"Sentence {index} ends here." for index in range(120)]
    chunks = chunk_document(" ".join(sentences))
    assert len(chunks) >= 3
    rejoined = " ".join(chunks)
    assert "Sentence 0 ends here." in rejoined
    assert "Sentence 119 ends here." in rejoined
    for chunk in chunks:
        assert len(chunk) <= CHUNK_CEILING


def test_consecutive_chunks_overlap_for_context() -> None:
    paragraphs = [f"P{index} " + "y" * 600 for index in range(3)]
    chunks = chunk_document("\n\n".join(paragraphs))
    assert len(chunks) >= 2
    first_tail = chunks[0][-OVERLAP_CHARS:].lstrip()
    assert first_tail
    assert chunks[1].startswith(first_tail[:40])


def test_content_hash_tracks_title_and_body() -> None:
    base = content_hash("Title", "Body text")
    assert base == content_hash("Title", "Body text")
    assert base != content_hash("Title", "Body text changed")
    assert base != content_hash("Title changed", "Body text")
