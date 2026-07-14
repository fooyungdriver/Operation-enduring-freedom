"""Shared pytest fixtures.

These tests never touch the network: Zoho and Claude are mocked. Printing uses
the built-in ``.prn`` fallback, so no printer is required either. That makes the
whole suite safe to run on any machine, including CI and Claude Code web sessions.
"""

from __future__ import annotations

import pytest

from app.server import app as flask_app


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


@pytest.fixture
def sample_generator() -> dict:
    return {
        "id": "100",
        "Name": "Acme Plating",
        "EPA_ID": "TXR000111222",
        "State_Registration_No": "TX-9988",
        "Generator_Status": "Active",
        "Site_Address_Line_1": "100 Industrial Rd",
        "Site_City": "Houston",
        "Site_State": "TX",
        "Site_ZIP": "77001",
        "Mailing_Address_Line_1": "PO Box 9",
        "Mailing_Address_City": "Houston",
        "Mailing_Address_State": "TX",
        "Mailing_Address_ZIP": "77002",
    }


@pytest.fixture
def sample_profiles() -> list[dict]:
    return [
        {
            "id": "p1",
            "Name": "Spent solvent",
            "DOT_Proper_Shipping_Name": "Waste flammable liquid n.o.s.",
            "DOT_Hazard_Class": "3",
            "DOT_UN_NA_Number": "UN1993",
            "DOT_Packing_Group": "II",
            "EPA_Waste_Codes": ["D001", "F003"],
            "Status": "Approved",
        }
    ]
