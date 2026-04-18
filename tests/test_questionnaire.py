"""Tests for questionnaire -- Step 3."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import json

import pytest

from rgen.questionnaire import Questionnaire
from rgen.models import ProjectProfile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def kb_dir(tmp_path: Path) -> Path:
    """Minimal knowledge_base with one pattern."""
    p = tmp_path / "knowledge_base" / "sample_pattern"
    p.mkdir(parents=True)
    (p / "metadata.json").write_text(json.dumps({
        "id": "sample_pattern",
        "name": "Sample Pattern",
        "tech_stack": ["python", "docker"],
        "agents": ["developer", "ops"],
    }), encoding="utf-8")
    (p / "routing-map.json").write_text(json.dumps({
        "infra": {"agent": "ops", "keywords": ["docker"], "files": [], "context": "", "priority": "high"}
    }), encoding="utf-8")
    return tmp_path / "knowledge_base"


# ---------------------------------------------------------------------------
# Path A — from existing pattern
# ---------------------------------------------------------------------------

def test_path_a_produces_projectprofile(kb_dir: Path, tmp_path: Path) -> None:
    q = Questionnaire(kb_dir)
    profile = q.run_with_defaults({
        "use_pattern": "y",
        "pattern_id": "sample_pattern",
        "project_name": "acme",
        "target_path": str(tmp_path / "output"),
    })
    assert isinstance(profile, ProjectProfile)
    assert profile.project_name == "acme"
    assert profile.pattern_id == "sample_pattern"
    assert profile.target_path == tmp_path / "output"


def test_path_a_sets_tech_stack_from_pattern(kb_dir: Path, tmp_path: Path) -> None:
    q = Questionnaire(kb_dir)
    profile = q.run_with_defaults({
        "use_pattern": "y",
        "pattern_id": "sample_pattern",
        "project_name": "acme",
        "target_path": str(tmp_path),
    })
    assert "python" in profile.tech_stack
    assert "docker" in profile.tech_stack


def test_path_a_sets_project_name_in_template_vars(kb_dir: Path, tmp_path: Path) -> None:
    q = Questionnaire(kb_dir)
    profile = q.run_with_defaults({
        "use_pattern": "y",
        "pattern_id": "sample_pattern",
        "project_name": "my-app",
        "target_path": str(tmp_path),
    })
    assert profile.template_vars["PROJECT_NAME"] == "my-app"


def test_path_a_agent_rename_stored_in_template_vars(kb_dir: Path, tmp_path: Path) -> None:
    q = Questionnaire(kb_dir)
    profile = q.run_with_defaults({
        "use_pattern": "y",
        "pattern_id": "sample_pattern",
        "project_name": "acme",
        "target_path": str(tmp_path),
        "rename_agent_developer": "backend",
    })
    assert profile.template_vars.get("RENAME_DEVELOPER") == "backend"


def test_path_a_falls_back_to_first_pattern_if_invalid(kb_dir: Path, tmp_path: Path) -> None:
    q = Questionnaire(kb_dir)
    profile = q.run_with_defaults({
        "use_pattern": "y",
        "pattern_id": "nonexistent_pattern",
        "project_name": "x",
        "target_path": str(tmp_path),
    })
    assert profile.pattern_id == "sample_pattern"


# ---------------------------------------------------------------------------
# Path B — from scratch
# ---------------------------------------------------------------------------

def test_path_b_produces_projectprofile(kb_dir: Path, tmp_path: Path) -> None:
    q = Questionnaire(kb_dir)
    profile = q.run_with_defaults({
        "use_pattern": "n",
        "project_name": "scratch-project",
        "target_path": str(tmp_path),
        "tech_stack": "python,fastapi,postgres",
        "domain_keywords": "auth,billing",
    })
    assert profile.project_name == "scratch-project"
    assert profile.pattern_id == ""
    assert profile.tech_stack == ["python", "fastapi", "postgres"]
    assert profile.domain_keywords == ["auth", "billing"]


def test_path_b_empty_tech_stack_is_allowed(kb_dir: Path, tmp_path: Path) -> None:
    q = Questionnaire(kb_dir)
    profile = q.run_with_defaults({
        "use_pattern": "n",
        "project_name": "bare",
        "target_path": str(tmp_path),
    })
    assert profile.tech_stack == []
    assert profile.domain_keywords == ["informatica"]


def test_path_b_strips_whitespace_from_lists(kb_dir: Path, tmp_path: Path) -> None:
    q = Questionnaire(kb_dir)
    profile = q.run_with_defaults({
        "use_pattern": "n",
        "project_name": "x",
        "target_path": str(tmp_path),
        "tech_stack": " python , docker , redis ",
        "domain_keywords": " auth , users ",
    })
    assert profile.tech_stack == ["python", "docker", "redis"]
    assert profile.domain_keywords == ["auth", "users"]


def test_path_b_numeric_multi_select_for_tech_and_domains(kb_dir: Path, tmp_path: Path) -> None:
    q = Questionnaire(kb_dir)
    profile = q.run_with_defaults({
        "use_pattern": "n",
        "project_name": "x",
        "target_path": str(tmp_path),
        "tech_stack": "1,6,15,custom-tech",
        "domain_keywords": "1,2,9,custom-domain",
    })
    assert profile.tech_stack == ["python", "typescript", "redis", "custom-tech"]
    assert profile.domain_keywords == ["informatica", "api", "docker_infra", "custom-domain"]


def test_project_selection_timeout_falls_back_to_default(kb_dir: Path) -> None:
    q = Questionnaire(kb_dir)
    with patch.object(Questionnaire, "_read_input_with_timeout", return_value=None):
        value = q._ask(
            "use_pattern",
            "Vuoi partire da un pattern esistente?",
            default="y",
            choices=("y", "n", "yes", "no"),
            timeout_seconds=30,
        )
    assert value == "y"


# ---------------------------------------------------------------------------
# Interactive mode (mocked input)
# ---------------------------------------------------------------------------

def test_run_interactive_path_b(kb_dir: Path, tmp_path: Path) -> None:
    answers = iter([
        "n",                   # use_pattern
        "my-project",          # project_name
        str(tmp_path),         # target_path
        "python,docker",       # tech_stack
        "api,storage",         # domain_keywords
    ])
    with patch("builtins.input", side_effect=answers):
        q = Questionnaire(kb_dir)
        profile = q.run()
    assert profile.project_name == "my-project"
    assert "python" in profile.tech_stack
