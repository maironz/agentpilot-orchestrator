"""Shared pytest fixtures."""

from pathlib import Path

import pytest

from rgen.models import ProjectProfile


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
