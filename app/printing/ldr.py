"""Render a Land Disposal Restriction (LDR) notification / certification.

Unlike the manifest, the LDR is typically not a controlled multi-part form, so
this starts as a clean, self-contained printed document (the layout below is
generated in full, not overprinted). If Red Arc uses a pre-printed LDR form,
switch to the same fixed-position approach as ``manifest_8700_22`` by placing
fields onto a grid instead of writing whole lines.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import escp


@dataclass
class LdrWaste:
    waste_code: str = ""
    description: str = ""
    subcategory: str = ""           # LDR subcategory / treatment standard ref
    meets_standard: bool = True     # certification: meets LDR treatment standard


@dataclass
class LdrData:
    generator_name: str = ""
    generator_epa_id: str = ""
    manifest_tracking_number: str = ""
    facility_name: str = ""
    date: str = ""
    wastes: list[LdrWaste] = field(default_factory=list)
    certification_statement: str = (
        "I certify under penalty of law that the waste described above meets the "
        "applicable Land Disposal Restriction treatment standards in 40 CFR 268."
    )
    signature_name: str = ""

    def summary(self) -> str:
        return (
            f"LDR — {self.generator_name or '(unknown generator)'}, "
            f"{len(self.wastes)} waste code(s), manifest "
            f"{self.manifest_tracking_number or '(n/a)'}"
        )


def build_page(data: LdrData) -> escp.TextPage:
    page = escp.TextPage()
    page.place(2, 20, "LAND DISPOSAL RESTRICTION NOTIFICATION / CERTIFICATION")
    page.place(4, 4, f"Generator: {data.generator_name}")
    page.place(5, 4, f"EPA ID: {data.generator_epa_id}")
    page.place(4, 50, f"Date: {data.date}")
    page.place(5, 50, f"Manifest #: {data.manifest_tracking_number}")
    page.place(6, 4, f"Designated facility: {data.facility_name}")

    page.place(9, 4, "Waste")
    page.place(9, 14, "Description")
    page.place(9, 50, "Subcategory")
    page.place(9, 70, "Meets std")
    page.place(10, 4, "-" * 78)

    row = 11
    for w in data.wastes:
        page.place(row, 4, w.waste_code)
        page.place_wrapped(row, 14, w.description, width=34, max_lines=2)
        page.place(row, 50, w.subcategory)
        page.place(row, 70, "Yes" if w.meets_standard else "No")
        row += 2

    row = max(row + 2, 40)
    page.place_wrapped(row, 4, data.certification_statement, width=78, max_lines=4)
    page.place(row + 6, 4, f"Signature: {data.signature_name}")
    page.place(row + 6, 50, "Date: ______________")
    return page


def render_ldr(
    data: LdrData,
    *,
    cpi: int = 10,
    lpi: int = 6,
    x_offset_chars: int = 0,
    y_offset_lines: int = 0,
) -> bytes:
    page = build_page(data)
    return escp.render(
        page,
        cpi=cpi,
        lpi=lpi,
        x_offset_chars=x_offset_chars,
        y_offset_lines=y_offset_lines,
    )


def preview_text(data: LdrData) -> str:
    return build_page(data).to_text()
