"""Embedding providers behind one interface: embed(texts) -> vectors.

No real provider is wired in yet (a local or hosted model comes later); the fake one is for tests.
"""
import hashlib
import math
import re
from typing import Protocol

DIMENSIONS = 1536


class EmbeddingError(Exception):
    pass


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


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
