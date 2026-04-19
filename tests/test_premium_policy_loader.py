"""Tests for optional premium policy loader boundary."""

from __future__ import annotations

from types import SimpleNamespace

from rgen.premium_policy_loader import load_policy_provider


class _PrivateProvider:
    def evaluate(self, policy_input):
        return {"provider": "private", "scenario": policy_input.scenario}


def test_policy_loader_uses_private_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        "rgen.premium_policy_loader.import_module",
        lambda _name: SimpleNamespace(get_policy_provider=lambda: _PrivateProvider()),
    )

    provider = load_policy_provider()

    assert isinstance(provider, _PrivateProvider)


def test_policy_loader_falls_back_when_module_missing(monkeypatch) -> None:
    def _raise(_name: str):
        raise ImportError("missing")

    monkeypatch.setattr("rgen.premium_policy_loader.import_module", _raise)

    provider = load_policy_provider()

    assert provider.__class__.__name__ == "DefaultPolicyProvider"


def test_policy_loader_falls_back_when_provider_invalid(monkeypatch) -> None:
    monkeypatch.setattr(
        "rgen.premium_policy_loader.import_module",
        lambda _name: SimpleNamespace(get_policy_provider=lambda: object()),
    )

    provider = load_policy_provider()

    assert provider.__class__.__name__ == "DefaultPolicyProvider"