"""Flask route tests with Zoho and printing mocked (no network, no printer)."""

from __future__ import annotations

import app.server as server


def test_index_and_static_pages(client):
    for path in ("/", "/calibration", "/settings",
                 "/skills/profile-from-sds", "/skills/waste-codes"):
        assert client.get(path).status_code == 200


def test_generators_unconfigured_shows_error(client, monkeypatch):
    # With no Zoho creds the client raises ZohoError; the page must render it.
    def boom():
        raise server.ZohoError("Zoho is not configured.")

    monkeypatch.setattr(server.zoho, "list_generators", boom)
    resp = client.get("/generators")
    assert resp.status_code == 200
    assert b"not configured" in resp.data.lower()


def test_generators_list_with_mock(client, monkeypatch, sample_generator):
    monkeypatch.setattr(server.zoho, "list_generators", lambda: [sample_generator])
    resp = client.get("/generators")
    assert b"Acme Plating" in resp.data
    assert b"TXR000111222" in resp.data


def test_generator_detail_with_mock(client, monkeypatch, sample_generator, sample_profiles):
    monkeypatch.setattr(server.zoho, "get_generator", lambda gid: sample_generator)
    monkeypatch.setattr(server.zoho, "list_profiles_for_generator", lambda gid: sample_profiles)
    resp = client.get("/generators/100")
    assert b"Acme Plating" in resp.data
    assert b"Spent solvent" in resp.data


def test_print_manifest_preview_and_print(client, monkeypatch, sample_generator, sample_profiles):
    monkeypatch.setattr(server.zoho, "get_generator", lambda gid: sample_generator)
    monkeypatch.setattr(server.zoho, "list_profiles_for_generator", lambda gid: sample_profiles)

    # GET shows a preview of where fields land.
    resp = client.get("/print/manifest/100")
    assert resp.status_code == 200
    assert b"Acme Plating" in resp.data

    # POST "print" must call send_raw exactly once; stub it so no file is written.
    calls = {}

    def fake_send_raw(data, *, printer_name, job_name):
        calls["bytes"] = data
        calls["job"] = job_name
        return "stub-destination"

    monkeypatch.setattr(server, "send_raw", fake_send_raw)
    resp = client.post(
        "/print/manifest/100",
        data={"action": "print", "tracking_number": "T-1", "profile_ids": "p1"},
        follow_redirects=True,
    )
    assert b"sent to stub-destination" in resp.data
    assert b"TXR000111222" in calls["bytes"]  # generator EPA ID overprinted


def test_skill_without_api_key_degrades(client):
    resp = client.post("/skills/waste-codes", data={"facts": "acetone", "state": "TX"})
    assert resp.status_code == 200
    assert b"not configured" in resp.data.lower()
