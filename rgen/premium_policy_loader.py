"""Optional loader for premium/private policy engine providers."""

from __future__ import annotations

from importlib import import_module

from rgen.policy_engine import DefaultPolicyProvider, PolicyProvider


def load_policy_provider() -> PolicyProvider:
    """Load a private policy provider when available, else use open-core default."""
    try:
        module = import_module("agentpilot_intelligence.policy")
    except Exception:
        return DefaultPolicyProvider()

    getter = getattr(module, "get_policy_provider", None)
    if getter is None or not callable(getter):
        return DefaultPolicyProvider()

    try:
        provider = getter()
    except Exception:
        return DefaultPolicyProvider()

    if provider is None or not hasattr(provider, "evaluate") or not callable(provider.evaluate):
        return DefaultPolicyProvider()

    return provider