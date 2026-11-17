"""Thin async client for the Onshape REST API (API-key auth)."""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import httpx


class OnshapeError(Exception):
    """Raised for any non-2xx response, with a message an agent can act on."""


_HINTS = {
    400: "The request was malformed - check IDs, the wvm type ('w', 'v' or 'm') and the body shape.",
    401: "Authentication failed - check ONSHAPE_ACCESS_KEY / ONSHAPE_SECRET_KEY.",
    403: "Forbidden - the API key lacks the needed scope (OAuth2Read/Write/Delete), or your permission on this document is too low (exports need Export permission, edits need Edit; check onshape_get_document -> permissionSet).",
    404: "Not found - verify document/workspace/element IDs (use onshape_parse_url on a browser URL).",
    409: "Conflict - the workspace may have changed; re-read and retry.",
    429: "Rate limited by Onshape - wait a moment and retry.",
}


@dataclass
class OnshapeRef:
    did: str
    wvm: str | None = None
    wvmid: str | None = None
    eid: str | None = None


_URL_RE = re.compile(
    r"/documents/(?P<did>[0-9a-f]{24})"
    r"(?:/(?P<wvm>[wvm])/(?P<wvmid>[0-9a-f]{24}))?"
    r"(?:/e/(?P<eid>[0-9a-f]{24}))?"
)


def parse_onshape_url(url: str) -> OnshapeRef:
    m = _URL_RE.search(url)
    if not m:
        raise OnshapeError(
            "Could not parse Onshape URL. Expected something like "
            "https://cad.onshape.com/documents/<did>/w/<wid>/e/<eid>"
        )
    return OnshapeRef(**m.groupdict())


class OnshapeClient:
    def __init__(
        self,
        access_key: str | None = None,
        secret_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.access_key = access_key or os.environ.get("ONSHAPE_ACCESS_KEY", "")
        self.secret_key = secret_key or os.environ.get("ONSHAPE_SECRET_KEY", "")
        self.base_url = (base_url or os.environ.get("ONSHAPE_BASE_URL") or "https://cad.onshape.com").rstrip("/")
        self._http = httpx.AsyncClient(timeout=httpx.Timeout(120.0), follow_redirects=False)

    def _auth_header(self) -> dict[str, str]:
        if not self.access_key or not self.secret_key:
            raise OnshapeError(
                "Missing Onshape credentials. Set ONSHAPE_ACCESS_KEY and ONSHAPE_SECRET_KEY "
                "(create keys at https://dev-portal.onshape.com/keys)."
            )
        token = base64.b64encode(f"{self.access_key}:{self.secret_key}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def _url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        if not path.startswith("/api/"):
            path = "/api/v10" + path
        return self.base_url + path

    async def request_raw(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        accept: str = "application/json",
    ) -> httpx.Response:
        headers = {**self._auth_header(), "Accept": accept}
        if json is not None:
            headers["Content-Type"] = "application/json"
        params = {k: v for k, v in (params or {}).items() if v is not None}
        url = self._url(path)
        # Follow redirects manually so the auth header is kept (exports redirect).
        for _ in range(5):
            resp = await self._http.request(method, url, params=params, json=json, headers=headers)
            if resp.status_code in (301, 302, 303, 307, 308) and "location" in resp.headers:
                url = urljoin(url, resp.headers["location"])
                params = None
                if resp.status_code == 303:
                    method, json = "GET", None
                continue
            break
        if resp.status_code >= 400:
            hint = _HINTS.get(resp.status_code, "")
            body = resp.text[:1500]
            raise OnshapeError(f"Onshape API {method} {path} -> HTTP {resp.status_code}. {hint}\nResponse: {body}")
        return resp

    async def request(self, method: str, path: str, **kw: Any) -> Any:
        resp = await self.request_raw(method, path, **kw)
        if not resp.content:
            return {"status": resp.status_code}
        try:
            return resp.json()
        except ValueError:
            return resp.text

    async def get(self, path: str, **kw: Any) -> Any:
        return await self.request("GET", path, **kw)

    async def post(self, path: str, **kw: Any) -> Any:
        return await self.request("POST", path, **kw)

    async def delete(self, path: str, **kw: Any) -> Any:
        return await self.request("DELETE", path, **kw)
