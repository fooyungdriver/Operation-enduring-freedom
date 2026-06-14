"""Thin Zoho CRM v8 client for the Red Arc Ops Tool.

Zoho CRM is the system of record. This module wraps the handful of REST
operations the app needs, handles OAuth2 access-token refresh, and retries
transient network failures with exponential backoff.

Design notes
------------
* We use the *refresh-token* grant. The owner generates a refresh token once
  (see README "Zoho one-time setup"); the app exchanges it for short-lived
  access tokens automatically and caches the access token in memory until it
  is near expiry.
* Module API names match what already exists / will exist in Red Arc's CRM:
  ``Generators`` (exists today), ``Waste_Profiles``, ``Lab_Pack_Inventory``,
  ``Manifest_Log`` (to be created in the Zoho UI — the app only reads/writes,
  it does not create modules).
* All public methods raise :class:`ZohoError` with a readable message on
  failure so the Flask layer can surface it to the user.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import requests

from .config import config

# How long before a token's stated expiry we proactively refresh it.
_TOKEN_REFRESH_SKEW_SECONDS = 60
# Network retry policy (mirrors the project's git retry guidance: 2s,4s,8s,16s).
_RETRY_BACKOFFS = (2, 4, 8, 16)


class ZohoError(RuntimeError):
    """Raised when a Zoho request cannot be completed."""


class ZohoClient:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._access_token: str | None = None
        self._access_token_expiry: float = 0.0

    # --- URLs -------------------------------------------------------------

    @property
    def _dc(self) -> str:
        return config.zoho_data_center

    @property
    def _accounts_url(self) -> str:
        return f"https://accounts.zoho.{self._dc}/oauth/v2/token"

    @property
    def _api_base(self) -> str:
        return f"https://www.zohoapis.{self._dc}/crm/v8"

    # --- Auth -------------------------------------------------------------

    def _refresh_access_token(self) -> str:
        if not config.zoho_ready():
            raise ZohoError(
                "Zoho is not configured. Fill in client_id, client_secret and "
                "refresh_token on the Settings page (or in config.json)."
            )
        params = {
            "refresh_token": config.get("zoho", "refresh_token"),
            "client_id": config.get("zoho", "client_id"),
            "client_secret": config.get("zoho", "client_secret"),
            "grant_type": "refresh_token",
        }
        resp = self._request_with_retry("POST", self._accounts_url, params=params)
        data = resp.json()
        token = data.get("access_token")
        if not token:
            # Zoho returns 200 with an "error" key on bad refresh tokens.
            raise ZohoError(
                f"Could not obtain a Zoho access token: {data.get('error', data)}"
            )
        self._access_token = token
        # expires_in is seconds (typically 3600).
        self._access_token_expiry = time.time() + int(data.get("expires_in", 3600))
        return token

    def _token(self) -> str:
        with self._lock:
            if (
                self._access_token is None
                or time.time() >= self._access_token_expiry - _TOKEN_REFRESH_SKEW_SECONDS
            ):
                return self._refresh_access_token()
            return self._access_token

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Zoho-oauthtoken {self._token()}"}

    # --- Low-level HTTP ---------------------------------------------------

    def _request_with_retry(
        self, method: str, url: str, **kwargs: Any
    ) -> requests.Response:
        """Issue a request, retrying only on network-level errors."""
        last_exc: Exception | None = None
        for attempt, backoff in enumerate((0, *_RETRY_BACKOFFS)):
            if backoff:
                time.sleep(backoff)
            try:
                resp = requests.request(method, url, timeout=30, **kwargs)
                return resp
            except requests.RequestException as exc:  # connection/timeout
                last_exc = exc
                continue
        raise ZohoError(f"Network error talking to Zoho: {last_exc}")

    def _api(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call a CRM endpoint, refreshing the token once on a 401."""
        url = f"{self._api_base}/{path.lstrip('/')}"
        for _ in range(2):  # one retry specifically for an expired token
            resp = self._request_with_retry(
                method,
                url,
                headers=self._auth_headers(),
                params=params,
                json=json_body,
            )
            if resp.status_code == 401:
                with self._lock:
                    self._access_token = None  # force refresh on next call
                continue
            if resp.status_code == 204:
                return {"data": []}  # Zoho returns 204 for "no records"
            try:
                payload = resp.json()
            except ValueError:
                raise ZohoError(
                    f"Zoho returned a non-JSON response ({resp.status_code})."
                )
            if resp.status_code >= 400:
                raise ZohoError(
                    f"Zoho API error {resp.status_code}: "
                    f"{payload.get('message') or payload}"
                )
            return payload
        raise ZohoError("Zoho authorization failed after refreshing the token.")

    # --- Records ----------------------------------------------------------

    def get_records(
        self,
        module: str,
        *,
        fields: list[str] | None = None,
        per_page: int = 200,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if fields:
            params["fields"] = ",".join(fields)
        return self._api("GET", f"/{module}", params=params).get("data", [])

    def get_record(self, module: str, record_id: str) -> dict[str, Any] | None:
        data = self._api("GET", f"/{module}/{record_id}").get("data", [])
        return data[0] if data else None

    def search_records(self, module: str, word: str) -> list[dict[str, Any]]:
        """Full-text search within a module (Zoho 'word' search)."""
        return self._api(
            "GET", f"/{module}/search", params={"word": word}
        ).get("data", [])

    def get_related_records(
        self, module: str, record_id: str, related_list_api_name: str
    ) -> list[dict[str, Any]]:
        return self._api(
            "GET", f"/{module}/{record_id}/{related_list_api_name}"
        ).get("data", [])

    def create_record(self, module: str, record: dict[str, Any]) -> str:
        """Create one record; returns the new record id."""
        payload = self._api("POST", f"/{module}", json_body={"data": [record]})
        items = payload.get("data", [])
        if not items or items[0].get("code") != "SUCCESS":
            raise ZohoError(f"Zoho rejected the new {module} record: {items}")
        return items[0]["details"]["id"]

    def update_record(
        self, module: str, record_id: str, record: dict[str, Any]
    ) -> None:
        body = {"data": [{**record, "id": record_id}]}
        payload = self._api("PUT", f"/{module}/{record_id}", json_body=body)
        items = payload.get("data", [])
        if not items or items[0].get("code") != "SUCCESS":
            raise ZohoError(f"Zoho rejected the update to {module}: {items}")

    # --- Domain helpers (the operations the UI actually uses) -------------

    GENERATORS = "Generators"
    WASTE_PROFILES = "Waste_Profiles"
    LAB_PACK_INVENTORY = "Lab_Pack_Inventory"
    MANIFEST_LOG = "Manifest_Log"

    def list_generators(self) -> list[dict[str, Any]]:
        return self.get_records(self.GENERATORS)

    def get_generator(self, generator_id: str) -> dict[str, Any] | None:
        return self.get_record(self.GENERATORS, generator_id)

    def search_generators(self, word: str) -> list[dict[str, Any]]:
        return self.search_records(self.GENERATORS, word)

    def list_profiles_for_generator(self, generator_id: str) -> list[dict[str, Any]]:
        """Profiles whose Generator lookup points at this generator.

        Uses COQL-style criteria search. The lookup field on Waste_Profiles is
        assumed to be ``Generator``; adjust if Red Arc names it differently.
        """
        return self._api(
            "GET",
            f"/{self.WASTE_PROFILES}/search",
            params={"criteria": f"(Generator.id:equals:{generator_id})"},
        ).get("data", [])

    def list_lab_packs_for_profile(self, profile_id: str) -> list[dict[str, Any]]:
        return self._api(
            "GET",
            f"/{self.LAB_PACK_INVENTORY}/search",
            params={"criteria": f"(Waste_Profile.id:equals:{profile_id})"},
        ).get("data", [])

    def create_manifest_log(self, record: dict[str, Any]) -> str:
        return self.create_record(self.MANIFEST_LOG, record)


# Shared instance imported by the rest of the app.
zoho = ZohoClient()
