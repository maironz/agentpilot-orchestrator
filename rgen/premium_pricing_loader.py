"""Optional loader for premium/private pricing registries.

This module provides a stable boundary from open core to optional private
extensions. If no private package is installed, the loader returns an empty
registry and the core keeps using default pricing.
"""

from __future__ import annotations

from importlib import import_module


def load_premium_pricing() -> dict[str, dict]:
    """Load premium pricing registry from an optional private package.

    Expected private API:
        agentpilot_intelligence.pricing.get_pricing_registry() -> dict[str, dict]
    """
    try:
        module = import_module("agentpilot_intelligence.pricing")
    except Exception:
        return {}

    getter = getattr(module, "get_pricing_registry", None)
    if getter is None or not callable(getter):
        return {}

    try:
        data = getter()
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}
    return data
