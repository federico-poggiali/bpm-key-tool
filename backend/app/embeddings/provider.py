"""Embedding providers behind one interface: embed(texts) -> vectors."""
import hashlib
import math
import re
from typing import Protocol

import httpx

DIMENSIONS = 1536


class EmbeddingError(Exception):
    pass


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIProvider:
    URL = "https://api.openai.com/v1/embeddings"
    BATCH = 96

    def __init__(self, api_key: str, model: str = "text-embedding-3-small",
                 client: httpx.Client | None = None):
        if not api_key:
            raise EmbeddingError("OPENAI_API_KEY is not set (see .env)")
        self._key = api_key
        self._model = model
        self._http = client or httpx.Client(timeout=30)

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.BATCH):
            batch = texts[i:i + self.BATCH]
            try:
                resp = self._http.post(
                    self.URL, headers={"Authorization": f"Bearer {self._key}"},
                    json={"model": self._model, "input": batch, "dimensions": DIMENSIONS})
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise EmbeddingError(f"OpenAI embeddings request failed: {exc}") from exc
            data = sorted(resp.json()["data"], key=lambda d: d["index"])
            out += [d["embedding"] for d in data]
        return out


class FakeProvider:
    """Deterministic bag-of-words vectors for tests: texts sharing words are close."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    @staticmethod
    def _one(text: str) -> list[float]:
        vec = [0.0] * DIMENSIONS
        for word in re.findall(r"\w+", text.lower()):
            vec[int(hashlib.sha256(word.encode()).hexdigest(), 16) % DIMENSIONS] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
