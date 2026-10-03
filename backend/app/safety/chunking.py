import hashlib
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Chunk:
    content: str
    page_number: int | None
    section_title: str | None
    metadata: dict[str, Any]
    content_hash: str


class SemanticChunker:
    """Split documents into semantic chunks while preserving metadata."""

    def __init__(self, max_chunk_size: int = 500, overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk_text(
        self,
        text: str,
        page_number: int | None = None,
        section_title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Split text into semantic chunks with preserved metadata."""
        if metadata is None:
            metadata = {}

        # Normalize text
        text = self._clean_text(text)

        # Split into paragraphs first
        paragraphs = self._split_paragraphs(text)

        chunks: list[Chunk] = []
        current_chunk = ""
        current_metadata = metadata.copy()

        for para in paragraphs:
            # If paragraph alone is too large, split it
            if len(para) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, page_number, section_title, current_metadata))
                    current_chunk = ""
                chunks.extend(self._split_large_chunk(para, page_number, section_title, current_metadata))
            # If adding paragraph would exceed limit, save current chunk
            elif len(current_chunk) + len(para) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, page_number, section_title, current_metadata))
                current_chunk = para
            # Otherwise, add to current chunk
            else:
                current_chunk = current_chunk + "\n\n" + para if current_chunk else para

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, page_number, section_title, current_metadata))

        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)
        # Remove control characters except newlines
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        return text.strip()

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_large_chunk(
        self, text: str, page_number: int | None, section_title: str | None, metadata: dict[str, Any]
    ) -> list[Chunk]:
        """Split a large chunk into smaller pieces with overlap."""
        chunks: list[Chunk] = []
        start = 0
        while start < len(text):
            end = start + self.max_chunk_size
            # Try to break at sentence boundary
            if end < len(text):
                last_period = text.rfind(".", start, end)
                last_question = text.rfind("?", start, end)
                last_exclamation = text.rfind("!", start, end)
                last_boundary = max(last_period, last_question, last_exclamation)
                if last_boundary > start:
                    end = last_boundary + 1
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(self._create_chunk(chunk_text, page_number, section_title, metadata))
            start = end - self.overlap if end < len(text) else end
        return chunks

    def _create_chunk(
        self, content: str, page_number: int | None, section_title: str | None, metadata: dict[str, Any]
    ) -> Chunk:
        """Create a chunk with hash."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        return Chunk(
            content=content,
            page_number=page_number,
            section_title=section_title,
            metadata=metadata,
            content_hash=content_hash,
        )
