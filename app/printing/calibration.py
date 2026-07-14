"""A calibration test pattern for aligning overprint to pre-printed forms.

Prints a character ruler and corner markers so the user can see exactly where
column 1 / line 1 land on their form, then adjust the X/Y offset on the
Calibration screen until the markers sit where the form's boxes begin.
"""

from __future__ import annotations

from . import escp


def build_page() -> escp.TextPage:
    page = escp.TextPage()
    # Column ruler across the top: tens digits then units.
    tens = "".join(str((c // 10) % 10) if c % 10 == 0 else " " for c in range(1, page.cols + 1))
    units = "".join(str(c % 10) for c in range(1, page.cols + 1))
    page.place(1, 1, tens)
    page.place(2, 1, units)

    # Row ruler down the left edge + a marker every 5 lines.
    for r in range(1, page.rows + 1):
        page.place(r, 1, str(r % 10))
        if r % 5 == 0:
            page.place(r, 3, f"<- line {r}")

    # Corner markers and a labeled box so misalignment is obvious.
    page.place(4, 14, "[GENERATOR ID BOX]")
    page.place(4, 58, "[TRACKING # BOX]")
    page.place(28, 8, "[FIRST WASTE LINE]")
    return page


def render(
    *, cpi: int = 10, lpi: int = 6, x_offset_chars: int = 0, y_offset_lines: int = 0
) -> bytes:
    return escp.render(
        build_page(),
        cpi=cpi,
        lpi=lpi,
        x_offset_chars=x_offset_chars,
        y_offset_lines=y_offset_lines,
    )


def preview_text() -> str:
    return build_page().to_text()
