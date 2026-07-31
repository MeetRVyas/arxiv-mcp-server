"""Tests for arxiv_mcp.validation."""

from __future__ import annotations

import pytest

from arxiv_mcp.errors import ValidationError
from arxiv_mcp.validation import (
    MAX_BATCH_SIZE,
    MAX_QUERY_LENGTH,
    validate_arxiv_id,
    validate_batch_ids,
    validate_category,
    validate_query,
)


class TestValidateArxivId:
    def test_new_style_id(self):
        assert validate_arxiv_id("2301.00001") == "2301.00001"

    def test_new_style_id_with_version(self):
        assert validate_arxiv_id("2301.00001v2") == "2301.00001v2"

    def test_old_style_id(self):
        assert validate_arxiv_id("cs/0001001") == "cs/0001001"

    def test_old_style_id_with_subject_class(self):
        assert validate_arxiv_id("math.GT/0309136v1") == "math.GT/0309136v1"

    def test_strips_surrounding_whitespace(self):
        assert validate_arxiv_id("  1706.03762  ") == "1706.03762"

    def test_empty_string_raises_validation_error_not_crash(self):
        """This is the exact input that used to crash with a raw IndexError (#2)."""
        with pytest.raises(ValidationError):
            validate_arxiv_id("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValidationError):
            validate_arxiv_id("   ")

    def test_none_raises(self):
        with pytest.raises(ValidationError):
            validate_arxiv_id(None)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "bad_id",
        ["not-a-valid-id", "12345", "abc.defgh", "2301", "'; DROP TABLE papers;--"],
    )
    def test_malformed_ids_raise(self, bad_id):
        with pytest.raises(ValidationError):
            validate_arxiv_id(bad_id)


class TestValidateQuery:
    def test_valid_query_passes_through(self):
        assert validate_query("attention is all you need") == "attention is all you need"

    def test_blank_raises(self):
        with pytest.raises(ValidationError):
            validate_query("   ")

    def test_too_long_raises(self):
        with pytest.raises(ValidationError):
            validate_query("x" * (MAX_QUERY_LENGTH + 1))

    def test_at_max_length_passes(self):
        validate_query("x" * MAX_QUERY_LENGTH)  # should not raise


class TestValidateCategory:
    @pytest.mark.parametrize("cat", ["cs.LG", "stat.ML", "q-bio.NC", "physics", "math.GT"])
    def test_valid_categories(self, cat):
        assert validate_category(cat) == cat

    @pytest.mark.parametrize("cat", ["", "   ", "???", "cs..LG", "x" * 40])
    def test_invalid_categories_raise(self, cat):
        with pytest.raises(ValidationError):
            validate_category(cat)


class TestValidateBatchIds:
    def test_valid_batch(self):
        ids = ["1706.03762", "1810.04805"]
        assert validate_batch_ids(ids) == ids

    def test_empty_list_raises(self):
        with pytest.raises(ValidationError):
            validate_batch_ids([])

    def test_over_max_size_raises(self):
        ids = [f"2301.{i:05d}" for i in range(MAX_BATCH_SIZE + 1)]
        with pytest.raises(ValidationError):
            validate_batch_ids(ids)

    def test_at_max_size_passes(self):
        ids = [f"2301.{i:05d}" for i in range(MAX_BATCH_SIZE)]
        validate_batch_ids(ids)  # should not raise

    def test_one_bad_id_in_batch_raises(self):
        with pytest.raises(ValidationError):
            validate_batch_ids(["1706.03762", "not-valid"])
