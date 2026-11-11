"""Offline embedding generation service (REQ-FR-013, AD-004, batch 2.11).

Generates 384-dimensional L2-normalised vectors using ``sentence-transformers``
``all-MiniLM-L6-v2``.

Two invariants hold across this module:

1. **Lazy loading, once per process.** Importing :mod:`ai.embeddings` never
   loads PyTorch weights or touches the network. The model is loaded on the
   first :func:`get_embedding_model` call and cached for the lifetime of the
   worker process, matching the pattern in :func:`ai.pii.get_nlp`.
2. **Offline and deterministic.** Text is whitespace-normalised before encoding,
   and every returned vector is an L2-normalised 384-float ``list[float]``.
   Tests inject a lightweight stub ``model`` via ``embed(..., model=stub)`` or
   ``embed_batch(..., model=stub)`` so unit suites run in milliseconds with zero
   network access.
"""

from __future__ import annotations

import math
import os
import re
from collections.abc import Sequence
from typing import Any, Protocol

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_WHITESPACE_RE = re.compile(r"\s+")
_MODEL_INSTANCE: Any = None


class EmbeddingModel(Protocol):
    """Minimal protocol required by :func:`embed` and :func:`embed_batch`.

    Matches ``sentence_transformers.SentenceTransformer.encode`` and allows
    deterministic test doubles without importing ``torch``.
    """

    def encode(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool = True,
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
    ) -> Any: ...


class EmbeddingError(RuntimeError):
    """Raised when the embedding model fails or returns an invalid vector."""


def normalize_embedding_text(text: str) -> str:
    """Collapse runs of whitespace so cosmetic formatting never shifts vectors."""
    if not isinstance(text, str):
        raise TypeError(f"embedding input must be str, got {type(text).__name__}")
    return _WHITESPACE_RE.sub(" ", text).strip()


def _l2_normalize(vec: Sequence[float]) -> list[float]:
    """Return a unit-length ``list[float]`` of length :data:`EMBEDDING_DIM`."""
    floats = [float(x) for x in vec]
    if len(floats) != EMBEDDING_DIM:
        raise EmbeddingError(
            f"expected {EMBEDDING_DIM}-dimensional vector, got {len(floats)}"
        )
    if any(math.isnan(x) or math.isinf(x) for x in floats):
        raise EmbeddingError("embedding vector contains NaN or Inf values")
    norm = math.sqrt(sum(x * x for x in floats))
    if norm == 0.0:
        raise EmbeddingError("embedding vector has zero L2 norm")
    return [x / norm for x in floats]


def get_embedding_model() -> Any:
    """Lazily load and cache the ``all-MiniLM-L6-v2`` ``SentenceTransformer``."""
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is None:
        from sentence_transformers import SentenceTransformer

        cache_dir = os.environ.get("SENTENCE_TRANSFORMERS_HOME") or None
        local_only = os.environ.get("HF_HUB_OFFLINE", "").lower() in {
            "1",
            "true",
            "yes",
        }
        try:
            _MODEL_INSTANCE = SentenceTransformer(
                MODEL_NAME,
                cache_folder=cache_dir,
                device="cpu",
                local_files_only=local_only,
            )
        except TypeError:
            # Older sentence-transformers releases without `local_files_only`.
            _MODEL_INSTANCE = SentenceTransformer(
                MODEL_NAME,
                cache_folder=cache_dir,
                device="cpu",
            )
    return _MODEL_INSTANCE


def reset_embedding_model_cache() -> None:
    """Clear the cached model instance (used by unit tests)."""
    global _MODEL_INSTANCE
    _MODEL_INSTANCE = None


def embed_batch(
    texts: Sequence[str],
    *,
    model: Any | None = None,
) -> list[list[float]]:
    """Embed a sequence of texts into 384-dimensional unit vectors.

    Preserves input order. Raises :class:`ValueError` if any text is empty after
    whitespace normalisation, and :class:`EmbeddingError` if the model fails or
    produces a vector of the wrong dimension.
    """
    if isinstance(texts, (str, bytes)):
        raise TypeError("embed_batch expects a sequence of strings, not a single str")

    cleaned: list[str] = []
    for idx, raw in enumerate(texts):
        normed = normalize_embedding_text(raw)
        if not normed:
            raise ValueError(f"cannot embed empty text at index {idx}")
        cleaned.append(normed)

    if not cleaned:
        return []

    active_model = model if model is not None else get_embedding_model()
    try:
        raw_vectors = active_model.encode(
            cleaned,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
    except Exception as exc:
        raise EmbeddingError(f"embedding model encode failed: {exc}") from exc

    if hasattr(raw_vectors, "tolist"):
        raw_list = raw_vectors.tolist()
    else:
        raw_list = list(raw_vectors)

    if len(raw_list) != len(cleaned):
        raise EmbeddingError(
            f"model returned {len(raw_list)} vectors for {len(cleaned)} inputs"
        )

    return [_l2_normalize(vec) for vec in raw_list]


def embed(
    text: str,
    *,
    model: Any | None = None,
) -> list[float]:
    """Embed a single text string into a 384-dimensional unit vector."""
    normed = normalize_embedding_text(text)
    if not normed:
        raise ValueError("cannot embed empty text")
    return embed_batch([normed], model=model)[0]
