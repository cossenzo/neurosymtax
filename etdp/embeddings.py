"""[neuro] Embedding back-ends and cosine-similarity helpers.

* ``sentence-transformers`` (default, local model)
* ``openai`` / ``gemini`` (provider embedding APIs)
* ``hashing`` – deterministic character n-gram vectors, no model download; intended for
  offline tests and dry runs only (it measures lexical, not semantic, similarity).
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod

import numpy as np

from .config import EmbeddingsConfig

logger = logging.getLogger(__name__)


def l2_normalize(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return x / norms


def cosine_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity between the rows of ``a`` and ``b``."""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    return l2_normalize(np.asarray(a, dtype=float)) @ l2_normalize(np.asarray(b, dtype=float)).T


class Embedder(ABC):
    """Text-to-vector model with an in-memory cache."""

    def __init__(self) -> None:
        self._cache: dict[str, np.ndarray] = {}

    @abstractmethod
    def _embed(self, texts: list[str]) -> np.ndarray:
        """Return one vector per text."""

    def embed(self, texts: list[str]) -> np.ndarray:
        missing = [t for t in dict.fromkeys(texts) if t not in self._cache]
        if missing:
            vectors = np.asarray(self._embed(missing), dtype=float)
            for t, v in zip(missing, vectors):
                self._cache[t] = v
        if not texts:
            return np.zeros((0, 1))
        return l2_normalize(np.vstack([self._cache[t] for t in texts]))

    def similarity(self, a: list[str], b: list[str]) -> np.ndarray:
        return cosine_matrix(self.embed(a), self.embed(b))


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model: str) -> None:
        super().__init__()
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model)

    def _embed(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


class OpenAIEmbedder(Embedder):
    def __init__(self, model: str) -> None:
        super().__init__()
        import openai

        self._client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self._model = model

    def _embed(self, texts: list[str]) -> np.ndarray:
        out = []
        for i in range(0, len(texts), 256):
            resp = self._client.embeddings.create(model=self._model, input=texts[i : i + 256])
            out.extend(d.embedding for d in resp.data)
        return np.asarray(out)


class GeminiEmbedder(Embedder):
    def __init__(self, model: str) -> None:
        super().__init__()
        from google import genai

        self._client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self._model = model

    def _embed(self, texts: list[str]) -> np.ndarray:
        out = []
        for i in range(0, len(texts), 100):
            resp = self._client.models.embed_content(model=self._model, contents=texts[i : i + 100])
            out.extend(e.values for e in resp.embeddings)
        return np.asarray(out)


class HashingEmbedder(Embedder):
    """Deterministic character 3–5-gram hashing vectors (offline; lexical similarity only)."""

    def __init__(self, n_features: int = 2**14) -> None:
        super().__init__()
        from sklearn.feature_extraction.text import HashingVectorizer

        self._vec = HashingVectorizer(analyzer="char_wb", ngram_range=(3, 5), n_features=n_features,
                                      alternate_sign=False, norm="l2", lowercase=True)

    def _embed(self, texts: list[str]) -> np.ndarray:
        return self._vec.transform(texts).toarray()


def create_embedder(cfg: EmbeddingsConfig) -> Embedder:
    """Instantiate the embedding back-end selected in ``config.yaml``."""
    if cfg.backend == "sentence-transformers":
        return SentenceTransformerEmbedder(cfg.model)
    if cfg.backend == "openai":
        return OpenAIEmbedder(cfg.model)
    if cfg.backend == "gemini":
        return GeminiEmbedder(cfg.model)
    logger.warning("using the hashing embedder: lexical similarity only, intended for tests")
    return HashingEmbedder()
