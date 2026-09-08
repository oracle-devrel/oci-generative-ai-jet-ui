from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ResearchChunk:
    chunk_index: int
    content: str
    source_heading: str | None = None


def _extract_blocks(markdown: str) -> list[tuple[str | None, str]]:
    current_heading: str | None = None
    current_lines: list[str] = []
    blocks: list[tuple[str | None, str]] = []

    def flush_paragraph() -> None:
        nonlocal current_lines
        if current_lines:
            paragraph = " ".join(line.strip() for line in current_lines if line.strip()).strip()
            if paragraph:
                blocks.append((current_heading, paragraph))
            current_lines = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("#"):
            flush_paragraph()
            current_heading = stripped.lstrip("#").strip() or current_heading
            continue
        if not stripped:
            flush_paragraph()
            continue
        current_lines.append(stripped)

    flush_paragraph()
    return blocks


def chunk_markdown(markdown: str, max_chars: int = 1200) -> list[ResearchChunk]:
    blocks = _extract_blocks(markdown)
    if not blocks:
        content = markdown.strip()
        return [ResearchChunk(chunk_index=0, content=content)] if content else []

    chunks: list[ResearchChunk] = []
    current_heading: str | None = None
    current_parts: list[str] = []
    current_len = 0
    max_paragraphs_per_chunk = 2

    for heading, paragraph in blocks:
        paragraph_len = len(paragraph)
        if current_parts and (
            current_len + paragraph_len + 2 > max_chars
            or len(current_parts) >= max_paragraphs_per_chunk
        ):
            chunks.append(
                ResearchChunk(
                    chunk_index=len(chunks),
                    content="\n\n".join(current_parts),
                    source_heading=current_heading,
                )
            )
            current_parts = []
            current_len = 0
            current_heading = heading

        if not current_parts:
            current_heading = heading

        if paragraph_len > max_chars:
            words = paragraph.split()
            buffer: list[str] = []
            for word in words:
                candidate = " ".join(buffer + [word]).strip()
                if buffer and len(candidate) > max_chars:
                    chunks.append(
                        ResearchChunk(
                            chunk_index=len(chunks),
                            content=" ".join(buffer),
                            source_heading=heading,
                        )
                    )
                    buffer = [word]
                else:
                    buffer.append(word)
            if buffer:
                chunks.append(
                    ResearchChunk(
                        chunk_index=len(chunks),
                        content=" ".join(buffer),
                        source_heading=heading,
                    )
                )
            current_parts = []
            current_len = 0
            current_heading = None
            continue

        current_parts.append(paragraph)
        current_len += paragraph_len + 2

    if current_parts:
        chunks.append(
            ResearchChunk(
                chunk_index=len(chunks),
                content="\n\n".join(current_parts),
                source_heading=current_heading,
            )
        )

    return chunks
