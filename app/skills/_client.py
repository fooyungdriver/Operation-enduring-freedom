"""Shared Anthropic client + helpers for the in-app Claude skills.

Follows the project's Claude API conventions:
- official ``anthropic`` SDK,
- model ``claude-opus-4-8`` (configurable),
- adaptive thinking,
- structured outputs via ``output_config.format`` for anything we parse,
- API key from config / env, never hardcoded.
"""

from __future__ import annotations

import json
from typing import Any

from ..config import config

try:
    import anthropic

    _HAVE_ANTHROPIC = True
except Exception:
    _HAVE_ANTHROPIC = False


class SkillError(RuntimeError):
    """Raised when a Claude skill cannot run (e.g. not configured)."""


_client: "anthropic.Anthropic | None" = None


def _get_client() -> "anthropic.Anthropic":
    global _client
    if not _HAVE_ANTHROPIC:
        raise SkillError(
            "The 'anthropic' package isn't installed. Run "
            "'pip install -r requirements.txt'."
        )
    if not config.anthropic_ready():
        raise SkillError(
            "Claude is not configured. Add your Anthropic API key on the "
            "Settings page (or in config.json)."
        )
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.get("anthropic", "api_key"))
    return _client


def _first_text_block(response: Any) -> str:
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


def call_text(system: str, user: str, *, max_tokens: int = 16000) -> str:
    """Plain text answer from Claude (adaptive thinking)."""
    client = _get_client()
    response = client.messages.create(
        model=config.anthropic_model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    if response.stop_reason == "refusal":
        raise SkillError("Claude declined this request.")
    return _first_text_block(response).strip()


def call_structured(
    system: str, user: str, schema: dict[str, Any], *, max_tokens: int = 16000
) -> dict[str, Any]:
    """Structured JSON answer constrained to ``schema``."""
    client = _get_client()
    response = client.messages.create(
        model=config.anthropic_model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    if response.stop_reason == "refusal":
        raise SkillError("Claude declined this request.")
    text = _first_text_block(response)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SkillError(f"Claude returned unparseable output: {exc}")
