"""Tests for mapping Zoho records into the printable ManifestData."""

from __future__ import annotations

from app.manifest_builder import build_manifest


def test_build_manifest_maps_generator_fields(sample_generator, sample_profiles):
    data = build_manifest(sample_generator, sample_profiles, tracking_number="ABC123")
    assert data.manifest_tracking_number == "ABC123"
    assert data.generator_id == "TXR000111222"
    assert data.generator_name == "Acme Plating"
    assert "100 Industrial Rd" in data.generator_site_address
    assert "Houston" in data.generator_site_address and "TX" in data.generator_site_address
    assert "PO Box 9" in data.generator_mailing_address


def test_build_manifest_waste_line_from_profile(sample_generator, sample_profiles):
    data = build_manifest(sample_generator, sample_profiles)
    assert len(data.waste_lines) == 1
    line = data.waste_lines[0]
    assert "Waste flammable liquid" in line.dot_description
    assert "UN1993" in line.dot_description
    # A list of codes should be flattened to a space-joined string.
    assert "D001" in line.waste_codes and "F003" in line.waste_codes


def test_build_manifest_without_profiles(sample_generator):
    data = build_manifest(sample_generator, [])
    assert data.waste_lines == []


def test_build_manifest_tolerates_missing_fields():
    # A sparse record must not raise — fields default to empty.
    data = build_manifest({"id": "1", "Name": "Tiny Co"}, [{"id": "x", "Name": "Mystery waste"}])
    assert data.generator_name == "Tiny Co"
    assert data.generator_id == ""
    assert len(data.waste_lines) == 1
