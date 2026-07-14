"""Skill: suggest EPA/state waste codes and LDR subcategories for a profile.

Given the known facts about a waste, suggest candidate codes WITH reasoning and
a confidence level, so the user can confirm. Explicitly decision-support, not a
determination.
"""

from __future__ import annotations

from typing import Any

from ._client import call_structured

_SYSTEM = (
    "You assist hazardous-waste staff with RCRA waste code identification. "
    "Given facts about a waste, suggest candidate federal EPA waste codes "
    "(D/F/K/P/U), likely applicable state codes if a state is given, and the "
    "relevant LDR treatment-standard subcategory references. For every "
    "suggestion give a one-line rationale and a confidence of high/medium/low. "
    "Do not assert a code as definite unless the facts clearly support it. This "
    "is a suggestion for a qualified person to verify."
)

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "epa_waste_codes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "code": {"type": "string"},
                    "rationale": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["code", "rationale", "confidence"],
            },
        },
        "state_waste_codes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "code": {"type": "string"},
                    "rationale": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                },
                "required": ["code", "rationale", "confidence"],
            },
        },
        "ldr_subcategories": {
            "type": "array",
            "items": {"type": "string"},
        },
        "caveats": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["epa_waste_codes", "ldr_subcategories", "caveats"],
}


def suggest_codes(
    waste_facts: str, *, state: str | None = None
) -> dict[str, Any]:
    user = "Suggest waste codes for this waste:\n\n" + waste_facts.strip()
    if state:
        user += f"\n\nGenerator state: {state}"
    return call_structured(_SYSTEM, user, _SCHEMA)
