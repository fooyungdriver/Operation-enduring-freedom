"""Assemble and render the EPA Uniform Hazardous Waste Manifest (Form 8700-22).

Two layers, kept deliberately separate:

1. :class:`ManifestData` / :class:`WasteLine` — a plain data object describing
   one manifest. It does not know about Zoho or printing. A future
   ``emanifest.py`` (RCRAInfo / e-Manifest API submission) will build the *same*
   object, so the data model is the stable seam between paper and electronic.

2. :func:`render_manifest` — lays the data onto a fixed-width grid at the box
   positions of the pre-printed 8700-22 and emits ESC/P bytes.

IMPORTANT: ``FIELD_POS`` and ``LINE_ITEM`` below are starting coordinates. The
exact box positions depend on the specific 8700-22 form revision and the
printer's top-of-form. They are tuned in practice from the Calibration screen
(global X/Y offset) plus, if needed, edits here. Print to a .prn / plain paper
first, then onto one sacrificial pre-printed form — never burn a stack tuning.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import escp


@dataclass
class WasteLine:
    """One line of Item 11 (US DOT description) + 12-14 quantities."""

    dot_description: str = ""        # proper shipping name, hazard class, UN/NA, PG
    containers_no: str = ""          # Item 12: number of containers
    containers_type: str = ""        # Item 12: container type code (e.g. DM, CY)
    quantity: str = ""               # Item 13: total quantity
    unit: str = ""                   # Item 14: unit wt/vol code (e.g. P, G)
    waste_codes: str = ""            # Item 13 (bottom) / right margin waste codes


@dataclass
class ManifestData:
    """Everything printed on one 8700-22 form."""

    manifest_tracking_number: str = ""           # Item 1 (right)
    generator_id: str = ""                        # Item 1 (left) — generator EPA ID
    generator_name: str = ""                      # Item 3
    generator_mailing_address: str = ""           # Item 3
    generator_site_address: str = ""              # Item 4
    generator_phone: str = ""

    transporter_1_name: str = ""                  # Item 5
    transporter_1_epa_id: str = ""                # Item 5
    transporter_2_name: str = ""                  # Item 7
    transporter_2_epa_id: str = ""                # Item 7

    facility_name: str = ""                       # Item 8 designated facility
    facility_address: str = ""                    # Item 8
    facility_epa_id: str = ""                      # Item 8
    facility_phone: str = ""

    waste_lines: list[WasteLine] = field(default_factory=list)
    special_handling: str = ""                    # Item 14 special handling / additional info

    def summary(self) -> str:
        return (
            f"Manifest {self.manifest_tracking_number or '(no tracking #)'} — "
            f"{self.generator_name or '(unknown generator)'} → "
            f"{self.facility_name or '(unknown TSDF)'}, "
            f"{len(self.waste_lines)} line(s)"
        )


# Starting box coordinates (1-based row, col) at 10 cpi / 6 lpi. Tune via
# calibration. Keep this map as the single place form layout lives.
FIELD_POS: dict[str, tuple[int, int]] = {
    "generator_id": (4, 14),
    "manifest_tracking_number": (4, 58),
    "generator_name": (7, 6),
    "generator_mailing_address": (8, 6),
    "generator_site_address": (10, 6),
    "generator_phone": (12, 6),
    "transporter_1_name": (16, 6),
    "transporter_1_epa_id": (16, 50),
    "transporter_2_name": (18, 6),
    "transporter_2_epa_id": (18, 50),
    "facility_name": (21, 6),
    "facility_address": (22, 6),
    "facility_epa_id": (21, 50),
    "facility_phone": (23, 6),
    "special_handling": (44, 6),
}

# Item 11-14 waste lines: first line starts here, each subsequent line is
# LINE_STRIDE rows lower. The form has 4 pre-printed line rows.
LINE_ITEM = {
    "first_row": 28,
    "stride": 3,
    "dot_col": 8,
    "containers_no_col": 50,
    "containers_type_col": 55,
    "quantity_col": 62,
    "unit_col": 72,
    "waste_codes_col": 76,
    "max_lines": 4,
}


def build_page(data: ManifestData) -> escp.TextPage:
    page = escp.TextPage()
    for key, (row, col) in FIELD_POS.items():
        page.place(row, col, getattr(data, key, ""))

    row = LINE_ITEM["first_row"]
    for line in data.waste_lines[: LINE_ITEM["max_lines"]]:
        page.place_wrapped(row, LINE_ITEM["dot_col"], line.dot_description,
                           width=38, max_lines=2)
        page.place(row, LINE_ITEM["containers_no_col"], line.containers_no)
        page.place(row, LINE_ITEM["containers_type_col"], line.containers_type)
        page.place(row, LINE_ITEM["quantity_col"], line.quantity)
        page.place(row, LINE_ITEM["unit_col"], line.unit)
        page.place(row, LINE_ITEM["waste_codes_col"], line.waste_codes)
        row += LINE_ITEM["stride"]
    return page


def render_manifest(
    data: ManifestData,
    *,
    cpi: int = 10,
    lpi: int = 6,
    x_offset_chars: int = 0,
    y_offset_lines: int = 0,
) -> bytes:
    """Render manifest ``data`` to ESC/P bytes for the dot-matrix printer."""
    page = build_page(data)
    return escp.render(
        page,
        cpi=cpi,
        lpi=lpi,
        x_offset_chars=x_offset_chars,
        y_offset_lines=y_offset_lines,
    )


def preview_text(data: ManifestData) -> str:
    """Plain-text preview of where fields land — for the UI and dev testing."""
    return build_page(data).to_text()
