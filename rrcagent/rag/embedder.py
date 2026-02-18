"""Embedding providers for the RAG pipeline.

Defines the Embedder protocol and implementations:
- MockEmbedder: Deterministic hash-based embeddings for testing.
- GeminiEmbedder: Google Gemini text-embedding-004 (requires API key).
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import urllib.request
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def embed(self, text: str) -> list[float]: ...
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class MockEmbedder:
    """Deterministic embedder for testing. Produces consistent vectors
    from text using a hash function — no API calls."""

    def __init__(self, dimension: int = 256):
        self.dimension = dimension

    def embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Extend hash to fill the dimension
        extended = h
        while len(extended) < self.dimension * 4:
            extended += hashlib.sha256(extended).digest()
        # Convert to floats and normalize
        values = list(struct.unpack(f"{self.dimension}f", extended[: self.dimension * 4]))
        # Normalize to unit vector
        magnitude = sum(v * v for v in values) ** 0.5
        if magnitude > 0:
            values = [v / magnitude for v in values]
        return values

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]


class GeminiEmbedder:
    """Google Gemini text-embedding-004 embedder.

    Requires GOOGLE_API_KEY environment variable or explicit api_key param.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-embedding-001",
    ):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GeminiEmbedder requires a Google API key. "
                "Pass api_key or set GOOGLE_API_KEY env var."
            )
        self.model = model
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    def embed(self, text: str) -> list[float]:
        url = (
            f"{self._base_url}/models/{self.model}:embedContent"
            f"?key={self.api_key}"
        )
        payload = json.dumps({
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
        }).encode()

        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        return data["embedding"]["values"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]
