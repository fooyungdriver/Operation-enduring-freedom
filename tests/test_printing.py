"""Tests for the document/print rendering — pure logic, no printer needed."""

from __future__ import annotations

from app.printing import calibration, escp
from app.printing import ldr as ldr_doc
from app.printing import manifest_8700_22 as manifest_doc


def test_textpage_place_and_clip():
    page = escp.TextPage(rows=5, cols=10)
    page.place(1, 1, "HELLO")
    assert page.to_text().splitlines()[0] == "HELLO"
    # Out-of-bounds placement must be ignored, not crash.
    page.place(99, 99, "X")
    page.place(2, 8, "OVERFLOWING")  # clipped to width
    assert len(page.to_text().splitlines()[1]) <= 10


def test_textpage_wrap():
    page = escp.TextPage(rows=10, cols=40)
    used = page.place_wrapped(1, 1, "one two three four five six", width=10, max_lines=3)
    assert 1 <= used <= 3


def test_line_spacing_math():
    # ESC 3 n where n = round(180/lpi): 6 lpi -> 30, 8 lpi -> 22 or 23.
    assert escp.set_line_spacing(6) == escp.ESC + b"3" + bytes([30])
    assert escp.set_line_spacing(8)[-1] in (22, 23)


def test_render_contains_controls_and_eject():
    page = escp.TextPage(rows=3, cols=10)
    page.place(1, 1, "HI")
    out = escp.render(page, cpi=10, lpi=6, eject=True)
    assert out.startswith(escp.reset())
    assert escp.set_pitch(10) in out
    assert b"HI" in out
    assert out.endswith(escp.FF)


def test_calibration_offsets_shift_output():
    base = escp.render(escp.TextPage(rows=3, cols=10), x_offset_chars=0, y_offset_lines=0)
    shifted = escp.render(escp.TextPage(rows=3, cols=10), x_offset_chars=5, y_offset_lines=2)
    # Y offset adds leading line feeds, so the shifted output is longer.
    assert shifted.count(b"\n") > base.count(b"\n")


def test_manifest_render_includes_key_fields():
    data = manifest_doc.ManifestData(
        manifest_tracking_number="012345678 JJK",
        generator_id="TXR000111222",
        generator_name="Acme Plating",
        waste_lines=[manifest_doc.WasteLine(dot_description="Waste flammable liquid", waste_codes="D001")],
    )
    out = manifest_doc.render_manifest(data)
    for token in (b"012345678 JJK", b"TXR000111222", b"Acme Plating", b"D001"):
        assert token in out


def test_ldr_and_calibration_render_nonempty():
    ld = ldr_doc.LdrData(
        generator_name="Acme Plating",
        wastes=[ldr_doc.LdrWaste(waste_code="D001", description="Ignitable")],
    )
    assert b"Acme Plating" in ldr_doc.render_ldr(ld)
    assert len(calibration.render()) > 0
    assert "GENERATOR ID BOX" in calibration.preview_text()
