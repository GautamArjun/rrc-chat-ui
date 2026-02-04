"""Vector store implementations for the RAG pipeline.

Defines the VectorStore protocol and implementations:
- MockVectorStore: In-memory brute-force cosine similarity for testing.
- PgVectorStore: PostgreSQL pgvector (requires database connection).
"""

from __future__ import annotations

import math
from typing import Protocol, runtime_checkable

from rrcagent.rag.chunker import Chunk


@runtime_checkable
class VectorStore(Protocol):
    def upsert(self, study_id: str, chunks: list[Chunk]) -> None: ...
    def search(self, study_id: str, query_embedding: list[float], top_k: int) -> list[Chunk]: ...


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class MockVectorStore:
    """In-memory vector store using brute-force cosine similarity."""

    def __init__(self):
        self._chunks: list[Chunk] = []

    def upsert(self, study_id: str, chunks: list[Chunk]) -> None:
        self._chunks.extend(chunks)

    def search(
        self, study_id: str, query_embedding: list[float], top_k: int
    ) -> list[Chunk]:
        # Filter by study_id
        candidates = [c for c in self._chunks if c.study_id == study_id]
        if not candidates:
            return []

        # Score by cosine similarity
        scored = []
        for chunk in candidates:
            if chunk.embedding is None:
                continue
            sim = _cosine_similarity(query_embedding, chunk.embedding)
            scored.append((sim, chunk))

        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]


class PgVectorStore:
    """PostgreSQL pgvector store.

    Requires a PostgreSQL connection with the pgvector extension.
    This is a stub — real implementation will use SQL queries.
    """

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def upsert(self, study_id: str, chunks: list[Chunk]) -> None:
        raise NotImplementedError(
            "PgVectorStore requires a PostgreSQL connection. "
            "Use MockVectorStore for testing."
        )

    def search(
        self, study_id: str, query_embedding: list[float], top_k: int
    ) -> list[Chunk]:
        raise NotImplementedError(
            "PgVectorStore requires a PostgreSQL connection. "
            "Use MockVectorStore for testing."
        )
