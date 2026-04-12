"""Tests for optional premium pricing loader boundary."""

from __future__ import annotations

from types import SimpleNamespace

from rgen.premium_pricing_loader import load_premium_pricing


def test_loader_returns_empty_when_module_missing(monkeypatch):
    def _raise_import_error(_name: str):
        raise ImportError("missing")

    monkeypatch.setattr("rgen.premium_pricing_loader.import_module", _raise_import_error)
    assert load_premium_pricing() == {}


def test_loader_returns_empty_when_getter_missing(monkeypatch):
    module = SimpleNamespace()
    monkeypatch.setattr("rgen.premium_pricing_loader.import_module", lambda _name: module)
    assert load_premium_pricing() == {}


def test_loader_returns_empty_when_getter_raises(monkeypatch):
    def _boom():
        raise RuntimeError("boom")

    module = SimpleNamespace(get_pricing_registry=_boom)
    monkeypatch.setattr("rgen.premium_pricing_loader.import_module", lambda _name: module)
    assert load_premium_pricing() == {}


def test_loader_returns_empty_when_payload_not_dict(monkeypatch):
    module = SimpleNamespace(get_pricing_registry=lambda: ["not", "a", "dict"])
    monkeypatch.setattr("rgen.premium_pricing_loader.import_module", lambda _name: module)
    assert load_premium_pricing() == {}


def test_loader_returns_registry_when_valid(monkeypatch):
    expected = {
        "premium-model": {
            "input_per_1k": 0.01,
            "output_per_1k": 0.03,
            "context_window": 128000,
        }
    }
    module = SimpleNamespace(get_pricing_registry=lambda: expected)
    monkeypatch.setattr("rgen.premium_pricing_loader.import_module", lambda _name: module)
    assert load_premium_pricing() == expected
