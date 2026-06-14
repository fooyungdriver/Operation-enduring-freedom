"""Skill: draft a waste profile from pasted SDS / waste description text.

Returns a structured draft the user reviews and edits before it is saved to the
Zoho ``Waste_Profiles`` module. This is a decision-support draft, NOT a
regulatory determination — the user is responsible for the final profile.
"""

from __future__ import annotations

from typing import Any

from ._client import call_structured

_SYSTEM = (
    "You are an assistant to hazardous-waste profiling staff at a permitted "
    "waste management company. Given a Safety Data Sheet or a waste description, "
    "extract the fields needed to draft a US RCRA hazardous waste profile. "
    "Only state what the text supports; use null/empty for anything not "
    "determinable and add it to 'needs_review'. Never invent EPA waste codes — "
    "suggest them only when the text clearly supports the listing or "
    "characteristic, and flag uncertain ones in 'needs_review'. This is a draft "
    "for a human to verify, not a final determination."
)

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "waste_name": {"type": "string"},
        "physical_state": {
            "type": "string",
            "enum": ["solid", "liquid", "sludge", "gas", "unknown"],
        },
        "process_generating_waste": {"type": "string"},
        "dot_proper_shipping_name": {"type": "string"},
        "dot_un_na_number": {"type": "string"},
        "dot_hazard_class": {"type": "string"},
        "dot_packing_group": {"type": "string"},
        "epa_waste_codes": {"type": "array", "items": {"type": "string"}},
        "state_waste_codes": {"type": "array", "items": {"type": "string"}},
        "hazard_characteristics": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["ignitability", "corrosivity", "reactivity", "toxicity", "none"],
            },
        },
        "flash_point_c": {"type": ["number", "null"]},
        "ph": {"type": ["number", "null"]},
        "key_constituents": {"type": "array", "items": {"type": "string"}},
        "needs_review": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Fields that are uncertain or unsupported by the text.",
        },
    },
    "required": [
        "waste_name",
        "physical_state",
        "epa_waste_codes",
        "hazard_characteristics",
        "needs_review",
    ],
}


def draft_profile(sds_or_description: str) -> dict[str, Any]:
    user = (
        "Draft a waste profile from the following SDS / waste description.\n\n"
        f"{sds_or_description.strip()}"
    )
    return call_structured(_SYSTEM, user, _SCHEMA)
