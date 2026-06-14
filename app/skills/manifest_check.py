"""Skill: check an assembled manifest for completeness before printing.

Takes the same :class:`ManifestData` the print engine uses and asks Claude to
flag missing or likely-wrong fields (e.g. empty EPA IDs, a DOT description with
no UN number, missing container counts). Returns structured findings so the UI
can show a checklist; it does NOT block printing — it advises.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..printing.manifest_8700_22 import ManifestData
from ._client import call_structured

_SYSTEM = (
    "You review draft US EPA Uniform Hazardous Waste Manifests (Form 8700-22) "
    "for completeness and obvious inconsistencies before they are printed. "
    "Check for: missing generator/transporter/facility EPA IDs, missing manifest "
    "tracking number, DOT descriptions lacking a proper shipping name / hazard "
    "class / UN-NA number / packing group, waste lines missing container counts "
    "or quantities/units, and missing waste codes. Report concrete findings with "
    "a severity. Do not rewrite the manifest; just flag issues for the user."
)

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "ready_to_print": {"type": "boolean"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "field": {"type": "string"},
                    "issue": {"type": "string"},
                    "severity": {
                        "type": "string",
                        "enum": ["blocker", "warning", "info"],
                    },
                },
                "required": ["field", "issue", "severity"],
            },
        },
    },
    "required": ["ready_to_print", "findings"],
}


def check_manifest(data: ManifestData) -> dict[str, Any]:
    import json

    user = (
        "Review this assembled manifest (JSON) for completeness:\n\n"
        + json.dumps(asdict(data), indent=2)
    )
    return call_structured(_SYSTEM, user, _SCHEMA)
