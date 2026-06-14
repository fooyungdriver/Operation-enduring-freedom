"""Tests for config loading, env-var precedence, and calibration persistence."""

from __future__ import annotations

import json

import app.config as config_mod
from app.config import Config


def test_env_var_overrides_file(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-from-env")
    cfg = Config()
    assert cfg.get("anthropic", "model") == "claude-from-env"


def test_get_default_when_missing():
    cfg = Config()
    assert cfg.get("nope", "missing", default="fallback") == "fallback"


def test_readiness_flags(monkeypatch):
    cfg = Config()
    cfg._data = {}  # nothing configured
    assert cfg.zoho_ready() is False
    assert cfg.anthropic_ready() is False
    cfg._data = {
        "zoho": {"client_id": "a", "client_secret": "b", "refresh_token": "c"},
        "anthropic": {"api_key": "k"},
    }
    assert cfg.zoho_ready() is True
    assert cfg.anthropic_ready() is True


def test_calibration_save_roundtrip(tmp_path, monkeypatch):
    # Redirect config writes to a temp file so the real config.json is untouched.
    tmp_cfg = tmp_path / "config.json"
    monkeypatch.setattr(config_mod, "CONFIG_PATH", tmp_cfg)

    cfg = Config()
    cfg.save_printing_calibration("manifest", {"x_offset_chars": 4, "y_offset_lines": 1})

    written = json.loads(tmp_cfg.read_text())
    assert written["printing"]["calibration"]["manifest"]["x_offset_chars"] == 4
    # And the in-memory view reflects the save.
    assert cfg.get("printing", "calibration", "manifest", "y_offset_lines") == 1
