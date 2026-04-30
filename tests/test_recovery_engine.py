"""
Tests for RecoveryEngine — error_class matrix, evaluate, classify_routing_result.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from recovery_engine import RecoveryEngine, RecoveryPolicy, DEFAULT_MATRIX


@pytest.fixture
def engine():
    return RecoveryEngine()


# ─── evaluate: retry cases ───

def test_timeout_first_attempt_should_retry(engine):
    dec = engine.evaluate("timeout", retry_count=0)
    assert dec.action == "retry"
    assert dec.should_retry is True
    assert dec.retries_remaining == 2


def test_timeout_second_attempt_should_retry(engine):
    dec = engine.evaluate("timeout", retry_count=1)
    assert dec.should_retry is True
    assert dec.retries_remaining == 1


def test_timeout_exhausted_no_retry(engine):
    dec = engine.evaluate("timeout", retry_count=2)
    assert dec.should_retry is False
    assert dec.retries_remaining == 0


def test_network_retry(engine):
    dec = engine.evaluate("network", retry_count=0)
    assert dec.action == "retry"
    assert dec.should_retry is True


# ─── evaluate: fallback cases ───

def test_ambiguity_fallback(engine):
    dec = engine.evaluate("ambiguity", retry_count=0)
    assert dec.action == "fallback"
    assert dec.should_retry is False
    assert dec.retries_remaining == 0


def test_unknown_first_attempt_fallback(engine):
    dec = engine.evaluate("unknown", retry_count=0)
    # action='fallback' → should_retry is False; but retries_remaining reflects budget
    assert dec.action == "fallback"
    assert dec.should_retry is False
    assert dec.retries_remaining == 1


def test_unknown_exhausted_fallback(engine):
    dec = engine.evaluate("unknown", retry_count=1)
    assert dec.should_retry is False
    assert dec.action == "fallback"


# ─── evaluate: abort cases ───

def test_policy_abort(engine):
    dec = engine.evaluate("policy", retry_count=0)
    assert dec.action == "abort"
    assert dec.should_retry is False
    assert dec.retries_remaining == 0


# ─── evaluate: unknown error_class ───

def test_unrecognized_error_class_falls_back_to_unknown(engine):
    dec = engine.evaluate("database_exploded", retry_count=0)
    # Falls back to "unknown" policy
    assert dec.error_class == "database_exploded"
    assert dec.action in ("retry", "fallback")  # unknown policy has retry allowed once


# ─── as_dict ───

def test_decision_as_dict(engine):
    dec = engine.evaluate("timeout", retry_count=0)
    d = dec.as_dict()
    assert "error_class" in d
    assert "action" in d
    assert "should_retry" in d
    assert "retries_remaining" in d
    assert "reason" in d
    assert "policy_source" in d


# ─── classify_routing_result ───

def test_classify_fallback_zero_confidence(engine):
    result = {"scenario": "_fallback", "confidence": 0.0, "needs_clarification": False}
    assert engine.classify_routing_result(result) == "ambiguity"


def test_classify_needs_clarification(engine):
    result = {"scenario": "python_code", "confidence": 0.3, "needs_clarification": True}
    assert engine.classify_routing_result(result) == "ambiguity"


def test_classify_policy_strict(engine):
    result = {
        "scenario": "auth",
        "confidence": 0.3,
        "needs_clarification": False,
        "policy": {"governance_mode": "strict"},
    }
    assert engine.classify_routing_result(result) == "policy"


def test_classify_none_for_good_routing(engine):
    result = {
        "scenario": "python_code",
        "confidence": 0.85,
        "needs_clarification": False,
        "policy": {"governance_mode": "guarded"},
    }
    assert engine.classify_routing_result(result) == "none"


def test_classify_fallback_with_nonzero_confidence(engine):
    result = {"scenario": "_fallback", "confidence": 0.2, "needs_clarification": False}
    assert engine.classify_routing_result(result) == "unknown"


# ─── matrix_summary ───

def test_matrix_summary_contains_all_classes(engine):
    summary = engine.matrix_summary()
    classes = {row["error_class"] for row in summary}
    assert {"timeout", "network", "ambiguity", "policy", "unknown"}.issubset(classes)


def test_matrix_summary_has_required_fields(engine):
    for row in engine.matrix_summary():
        assert "error_class" in row
        assert "action" in row
        assert "max_retries" in row
        assert "reason" in row


# ─── custom matrix ───

def test_custom_matrix_override(engine):
    custom = {
        "timeout": RecoveryPolicy(
            error_class="timeout",
            action="abort",
            max_retries=0,
            reason="Custom: abort on timeout",
        )
    }
    custom_engine = RecoveryEngine(custom_matrix=custom)
    dec = custom_engine.evaluate("timeout", retry_count=0)
    assert dec.action == "abort"
    assert dec.should_retry is False
