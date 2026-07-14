"""Configuration loading for the Red Arc Ops Tool.

Values are read from ``config.json`` in the project root (copy
``config.example.json`` to get started). Any value can be overridden by an
environment variable, which is the preferred way to supply secrets in a
packaged/installed deployment. Environment variables always win over the file.

Env var names mirror the JSON path, upper-cased and joined with ``_``:
    zoho.client_id            -> ZOHO_CLIENT_ID
    anthropic.api_key         -> ANTHROPIC_API_KEY
    printing.manifest_printer_name -> PRINTING_MANIFEST_PRINTER_NAME
    server.port               -> SERVER_PORT

Nothing in this module raises if a value is missing — callers decide what is
required. This lets the app boot (and the UI load) even before Zoho/Anthropic
credentials are filled in, so the owner can configure it from the Settings page.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()  # pick up a local .env if present (dev convenience)
except Exception:  # python-dotenv is optional at runtime
    pass

# Project root = the directory that contains this app/ package.
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
OUT_DIR = ROOT / "out"  # where .prn files land on non-Windows dev machines


def _load_file() -> dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(
                f"config.json is not valid JSON ({exc}). "
                f"Compare it against config.example.json."
            )
    return {}


class Config:
    """Read-only view over config.json + environment overrides."""

    def __init__(self) -> None:
        self._data = _load_file()

    def reload(self) -> None:
        self._data = _load_file()

    def save_printing_calibration(self, doc_type: str, offsets: dict[str, Any]) -> None:
        """Persist calibration offsets for 'manifest' or 'ldr' to config.json.

        Calibration values are not secrets, so writing them to the file is safe.
        Creates config.json if it doesn't exist yet.
        """
        data = _load_file()
        printing = data.setdefault("printing", {})
        calib = printing.setdefault("calibration", {})
        calib[doc_type] = {**calib.get(doc_type, {}), **offsets}
        CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self._data = data

    def get(self, *path: str, default: Any = None) -> Any:
        """Fetch a nested value, e.g. cfg.get("zoho", "client_id")."""
        env_key = "_".join(p.upper() for p in path)
        if env_key in os.environ and os.environ[env_key] != "":
            return os.environ[env_key]

        node: Any = self._data
        for key in path:
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node if node is not None else default

    # --- Convenience accessors -------------------------------------------

    @property
    def zoho_data_center(self) -> str:
        return self.get("zoho", "data_center", default="com")

    @property
    def anthropic_model(self) -> str:
        return self.get("anthropic", "model", default="claude-opus-4-8")

    @property
    def server_host(self) -> str:
        return self.get("server", "host", default="127.0.0.1")

    @property
    def server_port(self) -> int:
        return int(self.get("server", "port", default=5000))

    def zoho_ready(self) -> bool:
        return all(
            self.get("zoho", k)
            for k in ("client_id", "client_secret", "refresh_token")
        )

    def anthropic_ready(self) -> bool:
        return bool(self.get("anthropic", "api_key"))


# A single shared instance the rest of the app imports.
config = Config()

# Ensure the dev output folder exists so file-based printing never fails.
OUT_DIR.mkdir(exist_ok=True)
