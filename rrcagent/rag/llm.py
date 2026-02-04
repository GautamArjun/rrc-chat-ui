"""LLM providers for the RAG pipeline.

GeminiLLM calls the Google Gemini API for text generation.
"""

from __future__ import annotations

import json
import os
import urllib.request


class GeminiLLM:
    """Google Gemini LLM provider.

    Requires GOOGLE_API_KEY environment variable or explicit api_key param.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-2.5-flash",
    ):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GeminiLLM requires a Google API key. "
                "Pass api_key or set GOOGLE_API_KEY env var."
            )
        self.model = model
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    def generate(self, prompt: str) -> str:
        url = (
            f"{self._base_url}/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )
        payload = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
        }).encode()

        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read())
        return data["candidates"][0]["content"]["parts"][0]["text"]
