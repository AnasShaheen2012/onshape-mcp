"""Offline tests - no Onshape account or network needed."""

import asyncio

import pytest

from onshape_mcp import server
from onshape_mcp.client import OnshapeClient, OnshapeError, parse_onshape_url

DID, WID, EID = "0123456789abcdef01234567", "89abcdef0123456789abcdef", "fedcba9876543210fedcba98"


def test_tools_registered():
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    for expected in ("onshape_search_documents", "onshape_add_feature", "onshape_get_shaded_view", "onshape_api_request"):
        assert expected in names
    assert all(n.startswith("onshape_") for n in names)


def test_parse_full_url():
    ref = parse_onshape_url(f"https://cad.onshape.com/documents/{DID}/w/{WID}/e/{EID}")
    assert (ref.did, ref.wvm, ref.wvmid, ref.eid) == (DID, "w", WID, EID)


def test_parse_document_only_url():
    ref = parse_onshape_url(f"https://cad.onshape.com/documents/{DID}")
    assert ref.did == DID and ref.eid is None


def test_parse_bad_url():
    with pytest.raises(OnshapeError):
        parse_onshape_url("https://example.com/not-onshape")


def test_url_building():
    c = OnshapeClient("a", "b", "https://cad.onshape.com/")
    assert c._url("/documents") == "https://cad.onshape.com/api/v10/documents"
    assert c._url("documents") == "https://cad.onshape.com/api/v10/documents"
    assert c._url("/api/v6/documents") == "https://cad.onshape.com/api/v6/documents"


def test_missing_credentials_gives_clear_error(monkeypatch):
    monkeypatch.delenv("ONSHAPE_ACCESS_KEY", raising=False)
    monkeypatch.delenv("ONSHAPE_SECRET_KEY", raising=False)
    with pytest.raises(OnshapeError, match="ONSHAPE_ACCESS_KEY"):
        OnshapeClient()._auth_header()
