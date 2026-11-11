"""Unit tests for the offline embedding service (REQ-FR-013, AD-004, batch 2.11)."""

from __future__ import annotations

import hashlib
import math
from typing import Any
from unittest.mock import patch

import pytest

from ai.embeddings import (
    EMBEDDING_DIM,
    MODEL_NAME,
    EmbeddingError,
    embed,
    embed_batch,
    get_embedding_model,
    normalize_embedding_text,
    reset_embedding_model_cache,
)


class DeterministicStubModel:
    """Fast, offline stub that hashes each sentence into a 384-float vector."""

    def __init__(self, *, dim: int = EMBEDDING_DIM) -> None:
        self.dim = dim
        self.calls: list[list[str]] = []

    def encode(
        self,
        sentences: list[str],
        *,
        normalize_embeddings: bool = True,
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
    ) -> list[list[float]]:
        self.calls.append(list(sentences))
        rows: list[list[float]] = []
        for sentence in sentences:
            vals: list[float] = []
            counter = 0
            while len(vals) < self.dim:
                digest = hashlib.sha256(
                    f"{counter}:{sentence}".encode("utf-8")
                ).digest()
                for b in digest:
                    if len(vals) < self.dim:
                        vals.append((b - 127.5) / 127.5)
                counter += 1
            rows.append(vals)
        return rows


def test_constants_match_architecture_spec():
    assert MODEL_NAME == "all-MiniLM-L6-v2"
    assert EMBEDDING_DIM == 384


def test_normalize_embedding_text_collapses_whitespace():
    raw = "  Python \n\t  Django   PostgreSQL  \r\n "
    assert normalize_embedding_text(raw) == "Python Django PostgreSQL"


def test_normalize_embedding_text_rejects_non_string():
    with pytest.raises(TypeError, match="must be str"):
        normalize_embedding_text(123)  # type: ignore[arg-type]


def test_embed_returns_384_unit_vector_and_is_deterministic():
    stub = DeterministicStubModel()
    v1 = embed("Senior Python Engineer with Django and PostgreSQL", model=stub)
    v2 = embed("  Senior   Python\nEngineer with Django and PostgreSQL ", model=stub)

    assert len(v1) == 384
    assert all(isinstance(x, float) for x in v1)
    assert math.isclose(math.sqrt(sum(x * x for x in v1)), 1.0, rel_tol=1e-6)
    assert v1 == v2


def test_embed_distinct_inputs_produce_distinct_vectors():
    stub = DeterministicStubModel()
    v_py = embed("Python backend developer with PostgreSQL", model=stub)
    v_fe = embed("React TypeScript frontend design systems", model=stub)
    assert v_py != v_fe


def test_embed_rejects_empty_or_whitespace_only_text():
    stub = DeterministicStubModel()
    with pytest.raises(ValueError, match="cannot embed empty text"):
        embed("", model=stub)
    with pytest.raises(ValueError, match="cannot embed empty text"):
        embed("   \n\t  ", model=stub)
    assert stub.calls == []


def test_embed_batch_preserves_order_and_batches_in_single_encode_call():
    stub = DeterministicStubModel()
    texts = [
        "First resume text with Python",
        "Second resume text with Go",
        "Third resume text with Rust",
    ]
    batch_vecs = embed_batch(texts, model=stub)

    assert len(stub.calls) == 1
    assert len(batch_vecs) == 3
    for text, vec in zip(texts, batch_vecs, strict=True):
        single = embed(text, model=DeterministicStubModel())
        assert vec == single


def test_embed_batch_empty_sequence_returns_empty_list():
    stub = DeterministicStubModel()
    assert embed_batch([], model=stub) == []
    assert stub.calls == []


def test_embed_batch_rejects_bare_string():
    stub = DeterministicStubModel()
    with pytest.raises(TypeError, match="sequence of strings"):
        embed_batch("not a sequence of strings", model=stub)


def test_embed_batch_rejects_empty_element():
    stub = DeterministicStubModel()
    with pytest.raises(ValueError, match="cannot embed empty text at index 1"):
        embed_batch(["valid text", "   "], model=stub)


def test_embed_rejects_wrong_dimension():
    bad_stub = DeterministicStubModel(dim=128)
    with pytest.raises(
        EmbeddingError, match="expected 384-dimensional vector, got 128"
    ):
        embed("Valid text", model=bad_stub)


def test_embed_rejects_zero_norm_vector():
    class ZeroModel:
        def encode(self, sentences: list[str], **kwargs: Any) -> list[list[float]]:
            return [[0.0] * EMBEDDING_DIM for _ in sentences]

    with pytest.raises(EmbeddingError, match="zero L2 norm"):
        embed("Valid text", model=ZeroModel())


def test_embed_rejects_nan_vector():
    class NanModel:
        def encode(self, sentences: list[str], **kwargs: Any) -> list[list[float]]:
            vec = [1.0] * EMBEDDING_DIM
            vec[0] = float("nan")
            return [vec for _ in sentences]

    with pytest.raises(EmbeddingError, match="NaN or Inf"):
        embed("Valid text", model=NanModel())


def test_embed_wraps_model_runtime_exception():
    class CrashingModel:
        def encode(self, sentences: list[str], **kwargs: Any) -> list[list[float]]:
            raise RuntimeError("boom")

    with pytest.raises(EmbeddingError, match="embedding model encode failed: boom"):
        embed("Valid text", model=CrashingModel())


def test_get_embedding_model_loads_lazily_once_per_process():
    reset_embedding_model_cache()
    stub = DeterministicStubModel()
    with patch(
        "sentence_transformers.SentenceTransformer", return_value=stub
    ) as mock_cls:
        m1 = get_embedding_model()
        m2 = get_embedding_model()
        assert m1 is stub
        assert m2 is stub
        assert mock_cls.call_count == 1
        vec = embed("Lazy loaded model test")
        assert len(vec) == 384
    reset_embedding_model_cache()


@pytest.mark.slow
def test_real_sentence_transformer_model_when_cached_locally(monkeypatch):
    """Exercises real all-MiniLM-L6-v2 weights when present in local cache."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    reset_embedding_model_cache()
    try:
        model = get_embedding_model()
    except Exception as exc:
        reset_embedding_model_cache()
        pytest.skip(f"all-MiniLM-L6-v2 weights not cached locally offline: {exc}")

    try:
        v1 = embed("Python developer with Django and PostgreSQL", model=model)
        v2 = embed("Python engineer experienced in Django and Postgres", model=model)
        v3 = embed("Pastry chef specialising in sourdough bread", model=model)
        assert len(v1) == 384
        sim_related = sum(a * b for a, b in zip(v1, v2, strict=True))
        sim_unrelated = sum(a * b for a, b in zip(v1, v3, strict=True))
        assert sim_related > sim_unrelated
    finally:
        reset_embedding_model_cache()
