"""ESC/P control codes and a fixed-width text page for overprinting forms.

Overprinting pre-printed forms (like the EPA 8700-22 manifest) on a dot-matrix
printer is most reliable as *plain positioned text*: we lay every field onto a
character grid at a fixed (row, column), then emit the grid as ESC/P so only the
variable data prints — the box outlines are already on the carbonless form.

The :class:`TextPage` grid is printer-agnostic; :func:`render` turns it into
ESC/P bytes with the chosen pitch (CPI) and line spacing (LPI), applying a
global X/Y offset from the calibration settings so the whole page can be nudged
to line up with the pre-printed boxes.

ESC/P is the Epson standard understood by most dot-matrix printers (Epson LQ/FX
series, and OKI/IBM in Epson-emulation mode). If Red Arc's printer needs IBM
Proprinter or OKI Microline native codes, only this file changes.
"""

from __future__ import annotations

from dataclasses import dataclass

ESC = b"\x1b"
FF = b"\x0c"  # form feed — eject the page
CR = b"\r"
LF = b"\n"

# Pitch selectors (characters per inch).
_PITCH = {
    10: ESC + b"P",   # Pica  (10 cpi)
    12: ESC + b"M",   # Elite (12 cpi)
    15: ESC + b"g",   # Condensed-ish (15 cpi)
}


def reset() -> bytes:
    """ESC @ — reset the printer to its power-on defaults."""
    return ESC + b"@"


def set_pitch(cpi: int) -> bytes:
    return _PITCH.get(cpi, _PITCH[10])


def set_line_spacing(lpi: int) -> bytes:
    """Set line spacing in lines-per-inch using ESC 3 n (n/180 inch)."""
    # ESC 3 n sets spacing to n/180". 6 lpi -> 30/180, 8 lpi -> 22.5/180.
    n = max(1, min(255, round(180 / lpi)))
    return ESC + b"3" + bytes([n])


@dataclass
class TextPage:
    """A fixed-size character grid you place strings onto.

    rows/cols are sized for a US-Letter form at the page's pitch. Placement is
    clipped to the grid so a too-long value can never corrupt the layout.
    """

    rows: int = 66          # 11 inches * 6 lpi
    cols: int = 85          # ~8.5 inches * 10 cpi
    _grid: list[list[str]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._grid = [[" "] * self.cols for _ in range(self.rows)]

    def place(self, row: int, col: int, text: str) -> None:
        """Write ``text`` starting at (row, col). 1-based, like form box refs."""
        if text is None:
            return
        r = row - 1
        if not (0 <= r < self.rows):
            return
        for i, ch in enumerate(str(text)):
            c = (col - 1) + i
            if 0 <= c < self.cols:
                self._grid[r][c] = ch

    def place_wrapped(self, row: int, col: int, text: str, width: int,
                      max_lines: int = 4) -> int:
        """Word-wrap ``text`` into ``width`` columns. Returns lines used."""
        if not text:
            return 0
        words = str(text).split()
        lines: list[str] = []
        current = ""
        for word in words:
            if len(current) + len(word) + (1 if current else 0) <= width:
                current = f"{current} {word}".strip()
            else:
                if current:
                    lines.append(current)
                current = word[:width]
            if len(lines) >= max_lines:
                break
        if current and len(lines) < max_lines:
            lines.append(current)
        for i, line in enumerate(lines[:max_lines]):
            self.place(row + i, col, line)
        return len(lines[:max_lines])

    def to_text(self) -> str:
        """Plain-text preview of the grid (trailing blanks trimmed)."""
        return "\n".join("".join(r).rstrip() for r in self._grid).rstrip() + "\n"


def render(
    page: TextPage,
    *,
    cpi: int = 10,
    lpi: int = 6,
    x_offset_chars: int = 0,
    y_offset_lines: int = 0,
    eject: bool = True,
) -> bytes:
    """Serialize a :class:`TextPage` to ESC/P bytes with calibration offsets."""
    out = bytearray()
    out += reset()
    out += set_pitch(cpi)
    out += set_line_spacing(lpi)

    # Vertical offset: blank lines before the content begins.
    for _ in range(max(0, y_offset_lines)):
        out += LF

    pad = " " * max(0, x_offset_chars)
    for row in page._grid:
        line = "".join(row).rstrip()
        if line:
            out += (pad + line).encode("ascii", errors="replace")
        out += CR + LF

    if eject:
        out += FF
    return bytes(out)
