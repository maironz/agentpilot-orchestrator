"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from rgen.models import ProjectProfile
import sys


@pytest.fixture
def no_network_scan(monkeypatch):
    """Blocca l'accesso ai drive di rete (Z:/) in audit_routing_coverage().

    Necessario perché Path('Z:/...').exists() su Windows con drive di rete
    non disponibili causa un blocco da timeout del sistema operativo.
    """
    sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
    import router_audit
    monkeypatch.setattr(router_audit, "_resolve_scan_path", lambda _candidates: None)


@pytest.fixture
def sample_profile(tmp_path: Path) -> ProjectProfile:
    """A minimal ProjectProfile pointing at tmp_path."""
    return ProjectProfile(
        project_name="test-project",
        target_path=tmp_path,
        pattern_id="psm_stack",
        template_vars={
            "PROJECT_NAME": "test-project",
            "DEV_AGENT": "developer",
        },
        tech_stack=["python", "docker"],
        domain_keywords=["auth", "api", "database"],
    )
