"""RAG service — the public API for FAQ answering.

Orchestrates: document indexing (chunk -> embed -> store)
and question answering (embed query -> search -> LLM generate).
"""

from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from rrcagent.rag.chunker import Chunk, load_and_chunk


@runtime_checkable
class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str: ...


# Patterns that indicate coaching language in LLM output
_COACHING_PATTERNS = [
    re.compile(r"to qualify", re.IGNORECASE),
    re.compile(r"you should (say|answer|report|claim|state)", re.IGNORECASE),
    re.compile(r"in order to (be eligible|pass|qualify)", re.IGNORECASE),
    re.compile(r"make sure (you|to) (say|answer|report)", re.IGNORECASE),
]

_SAFE_FALLBACK = (
    "I can only share information from the study FAQ. "
    "I can't provide guidance on how to qualify."
)


class RagService:
    """FAQ answering service backed by document retrieval and LLM generation."""

    def __init__(self, embedder, store, llm, top_k: int = 3):
        self._embedder = embedder
        self._store = store
        self._llm = llm
        self._top_k = top_k

    def index_document(self, study_id: str, file_path: str) -> int:
        """Load, chunk, embed, and store a document.

        Returns the number of chunks indexed.
        """
        chunks = load_and_chunk(file_path, study_id=study_id)
        if not chunks:
            return 0

        texts = [c.text for c in chunks]
        embeddings = self._embedder.embed_batch(texts)

        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        self._store.upsert(study_id, chunks)
        return len(chunks)

    def answer(
        self, question: str, study_id: str
    ) -> dict:
        """Answer a question using retrieved FAQ context.

        Returns dict with 'text' (answer string) and 'references' (list of
        source/chunk_index dicts).
        """
        query_embedding = self._embedder.embed(question)
        results = self._store.search(study_id, query_embedding, top_k=self._top_k)

        if not results:
            return {
                "text": "I don't have information about that in the study FAQ.",
                "references": [],
            }

        # Build context from retrieved chunks
        context_parts = []
        references = []
        for chunk in results:
            context_parts.append(chunk.text)
            references.append({
                "source": chunk.source,
                "chunk_index": chunk.chunk_index,
            })

        context = "\n\n".join(context_parts)

        # Build prompt
        prompt = (
            "You are a helpful assistant answering questions about a clinical study. "
            "Answer based on the provided context. If the user's question relates to "
            "any topic covered in the context, provide the relevant information even if "
            "the wording differs. Be generous in matching intent — for example, a question "
            "about 'how would I be paid' should be answered with compensation details. "
            "Do NOT provide guidance on how to qualify for the study. "
            "Do NOT mention eligibility criteria or screening logic. "
            "Only say you don't have the information if the context is entirely unrelated "
            "to the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )

        raw_answer = self._llm.generate(prompt)

        # Guardrail check
        if _contains_coaching(raw_answer):
            return {"text": _SAFE_FALLBACK, "references": references}

        return {"text": raw_answer, "references": references}


def _contains_coaching(text: str) -> bool:
    """Check if text contains coaching language."""
    return any(p.search(text) for p in _COACHING_PATTERNS)
