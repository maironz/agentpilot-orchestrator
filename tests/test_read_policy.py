"""Tests for rgen/read_policy.py — F1/F2 sensitive file read policy."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from rgen.read_policy import ReadPolicy, ReadPolicyViolation


# ---------------------------------------------------------------------------
# is_sensitive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", [
    ".env",
    ".ENV",
    ".env.local",
    ".env.production",
    "secrets",
    "secrets.yaml",
    "secrets.json",
    "server.pem",
    "private.key",
    "keystore.pfx",
    "keystore.p12",
    "credentials",
    "credentials.json",
    ".netrc",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa.pub",
])
def test_is_sensitive_true(name, tmp_path):
    rp = ReadPolicy(project_root=tmp_path)
    assert rp.is_sensitive(tmp_path / name), f"Expected {name!r} to be sensitive"


@pytest.mark.parametrize("name", [
    ".env.example",     # only matches if it passes .env.* — it does! see below
    "config.yaml",
    "README.md",
    "requirements.txt",
    "main.py",
    "data.json",
    "public.crt",       # certificate (not key)
    "mykey_manager.py", # not a bare .key file
])
def test_is_sensitive_false(name, tmp_path):
    rp = ReadPolicy(project_root=tmp_path)
    # .env.example matches .env\..+ so it IS sensitive — we skip it here
    if name == ".env.example":
        pytest.skip(".env.example intentionally matches .env.* pattern")
    assert not rp.is_sensitive(tmp_path / name), f"Expected {name!r} to be safe"


def test_env_example_is_sensitive():
    """.env.example matches the .env.* pattern (intended behavior)."""
    rp = ReadPolicy()
    assert rp.is_sensitive(".env.example")


# ---------------------------------------------------------------------------
# check_read / read_file — non-strict (warns)
# ---------------------------------------------------------------------------


def test_check_read_safe_file_no_warning(tmp_path):
    rp = ReadPolicy(project_root=tmp_path, strict=False)
    (tmp_path / "config.yaml").write_text("key: value", encoding="utf-8")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        rp.check_read(tmp_path / "config.yaml")
    assert not w


def test_check_read_sensitive_warns(tmp_path):
    rp = ReadPolicy(project_root=tmp_path, strict=False)
    env = tmp_path / ".env"
    env.write_text("SECRET=x", encoding="utf-8")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        rp.check_read(env)
    assert any("sensitive" in str(x.message) for x in w)


def test_read_file_sensitive_warns_but_returns_content(tmp_path):
    rp = ReadPolicy(project_root=tmp_path, strict=False)
    env = tmp_path / ".env"
    env.write_text("KEY=value", encoding="utf-8")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        content = rp.read_file(env)
    assert content == "KEY=value"
    assert any("sensitive" in str(x.message) for x in w)


# ---------------------------------------------------------------------------
# check_read / read_file — strict (raises)
# ---------------------------------------------------------------------------


def test_check_read_strict_raises(tmp_path):
    rp = ReadPolicy(project_root=tmp_path, strict=True)
    env = tmp_path / ".env"
    env.write_text("SECRET=x", encoding="utf-8")
    with pytest.raises(ReadPolicyViolation, match="sensitive"):
        rp.check_read(env)


def test_read_file_strict_raises(tmp_path):
    rp = ReadPolicy(project_root=tmp_path, strict=True)
    key = tmp_path / "private.key"
    key.write_text("-----BEGIN KEY-----", encoding="utf-8")
    with pytest.raises(ReadPolicyViolation):
        rp.read_file(key)


def test_read_bytes_strict_raises(tmp_path):
    rp = ReadPolicy(project_root=tmp_path, strict=True)
    pem = tmp_path / "cert.pem"
    pem.write_bytes(b"CERT")
    with pytest.raises(ReadPolicyViolation):
        rp.read_bytes(pem)


# ---------------------------------------------------------------------------
# allow / deny
# ---------------------------------------------------------------------------


def test_allow_suppresses_warning(tmp_path):
    rp = ReadPolicy(project_root=tmp_path, strict=False)
    env = tmp_path / ".env"
    env.write_text("KEY=x", encoding="utf-8")
    rp.allow(env)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        rp.check_read(env)
    assert not any("sensitive" in str(x.message) for x in w)


def test_allow_suppresses_strict_raise(tmp_path):
    rp = ReadPolicy(project_root=tmp_path, strict=True)
    env = tmp_path / ".env"
    env.write_text("KEY=x", encoding="utf-8")
    rp.allow(env)
    rp.check_read(env)  # Must not raise


def test_deny_removes_from_allowlist(tmp_path):
    rp = ReadPolicy(project_root=tmp_path, strict=True)
    env = tmp_path / ".env"
    env.write_text("KEY=x", encoding="utf-8")
    rp.allow(env)
    rp.deny(env)
    with pytest.raises(ReadPolicyViolation):
        rp.check_read(env)


def test_allowed_paths_constructor(tmp_path):
    env = tmp_path / ".env"
    env.write_text("KEY=x", encoding="utf-8")
    rp = ReadPolicy(project_root=tmp_path, strict=True, allowed_paths=[env])
    rp.check_read(env)  # Must not raise


# ---------------------------------------------------------------------------
# PolicyViolation hierarchy
# ---------------------------------------------------------------------------


def test_read_policy_violation_is_runtime_error():
    assert issubclass(ReadPolicyViolation, RuntimeError)


# ---------------------------------------------------------------------------
# sensitive_patterns property
# ---------------------------------------------------------------------------


def test_sensitive_patterns_returns_list():
    rp = ReadPolicy()
    pats = rp.sensitive_patterns
    assert isinstance(pats, list)
    assert len(pats) > 0
    assert all(isinstance(p, str) for p in pats)
