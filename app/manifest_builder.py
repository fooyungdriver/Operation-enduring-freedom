"""Map Zoho CRM records into the printable :class:`ManifestData` object.

Generator field API names are the ones already present in Red Arc's CRM. Waste
profile field names are best-effort (looked up with ``.get`` so a missing or
differently-named field never crashes the app) and should be confirmed against
the real Waste_Profiles module during build.
"""

from __future__ import annotations

from typing import Any

from .printing.manifest_8700_22 import ManifestData, WasteLine


def _join(*parts: str | None, sep: str = ", ") -> str:
    return sep.join(p for p in (x.strip() if isinstance(x, str) else "" for x in parts) if p)


def _site_address(gen: dict[str, Any]) -> str:
    return _join(
        gen.get("Site_Address_Line_1"),
        gen.get("Site_Address_Line_2"),
        _join(gen.get("Site_City"), gen.get("Site_State"), gen.get("Site_ZIP"), sep=" "),
    )


def _mailing_address(gen: dict[str, Any]) -> str:
    return _join(
        gen.get("Mailing_Address_Line_1"),
        gen.get("Mailing_Address_Line_2"),
        _join(
            gen.get("Mailing_Address_City"),
            gen.get("Mailing_Address_State"),
            gen.get("Mailing_Address_ZIP"),
            sep=" ",
        ),
    )


def _profile_to_waste_line(profile: dict[str, Any]) -> WasteLine:
    codes = profile.get("EPA_Waste_Codes") or profile.get("Waste_Codes") or ""
    if isinstance(codes, list):
        codes = " ".join(str(c) for c in codes)
    return WasteLine(
        dot_description=_join(
            profile.get("DOT_Proper_Shipping_Name") or profile.get("Name"),
            profile.get("DOT_Hazard_Class"),
            profile.get("DOT_UN_NA_Number"),
            profile.get("DOT_Packing_Group"),
            sep=", ",
        ),
        waste_codes=str(codes),
    )


def build_manifest(
    generator: dict[str, Any],
    profiles: list[dict[str, Any]] | None = None,
    *,
    tracking_number: str = "",
) -> ManifestData:
    """Assemble a ManifestData from a generator record and selected profiles."""
    profiles = profiles or []
    return ManifestData(
        manifest_tracking_number=tracking_number,
        generator_id=generator.get("EPA_ID", "") or "",
        generator_name=generator.get("Name", "") or "",
        generator_mailing_address=_mailing_address(generator),
        generator_site_address=_site_address(generator),
        waste_lines=[_profile_to_waste_line(p) for p in profiles],
    )
