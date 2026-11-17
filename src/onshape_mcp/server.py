"""Onshape MCP server (stdio).

Exposes Onshape documents, Part Studios, assemblies, features, variables,
FeatureScript evaluation, rendered views and STL export as MCP tools.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Literal

from mcp.server.mcpserver import Image, MCPServer
from mcp_types import ToolAnnotations

from .client import OnshapeClient, OnshapeError, parse_onshape_url

mcp = MCPServer("onshape_mcp", instructions="Tools for Onshape CAD. Most tools take did (document id), wvm (w=workspace, v=version, m=microversion), wvmid and eid (element/tab id). Use onshape_parse_url on a browser URL to get them. Writes require wvm=w.")
_client: OnshapeClient | None = None

WVM = Literal["w", "v", "m"]
READ = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)
WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=True)
DESTRUCTIVE = ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True, openWorldHint=True)


def client() -> OnshapeClient:
    global _client
    if _client is None:
        _client = OnshapeClient()
    return _client


def _p(did: str, wvm: str, wvmid: str, eid: str | None = None) -> str:
    path = f"/d/{did}/{wvm}/{wvmid}"
    return path + (f"/e/{eid}" if eid else "")


def _dump(data: Any, max_chars: int = 60000) -> str:
    text = json.dumps(data, indent=1, default=str)
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n... [truncated, {len(text)} chars total - narrow the request]"
    return text


async def _run(coro) -> str:
    try:
        return _dump(await coro)
    except OnshapeError as e:
        return f"Error: {e}"


# --------------------------------------------------------------------------- helpers


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
def onshape_parse_url(url: str) -> str:
    """Extract document id (did), wvm type, workspace/version/microversion id and element id (eid)
    from an Onshape browser URL like https://cad.onshape.com/documents/<did>/w/<wid>/e/<eid>."""
    try:
        return _dump(parse_onshape_url(url).__dict__)
    except OnshapeError as e:
        return f"Error: {e}"


# --------------------------------------------------------------------------- documents


@mcp.tool(annotations=READ)
async def onshape_search_documents(
    query: str = "",
    filter: int = 0,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """Search/list Onshape documents. filter: 0=my docs, 1=created by me, 2=shared with me,
    3=trash, 4=public, 6=recently opened. Returns id, name, owner, default workspace and modified date."""
    try:
        data = await client().get(
            "/documents", params={"q": query or None, "filter": filter, "limit": limit, "offset": offset}
        )
    except OnshapeError as e:
        return f"Error: {e}"
    items = [
        {
            "id": d.get("id"),
            "name": d.get("name"),
            "owner": (d.get("owner") or {}).get("name"),
            "defaultWorkspaceId": (d.get("defaultWorkspace") or {}).get("id"),
            "modifiedAt": d.get("modifiedAt"),
            "href": f"{client().base_url}/documents/{d.get('id')}",
        }
        for d in data.get("items", [])
    ]
    return _dump({"count": len(items), "offset": offset, "hasMore": bool(data.get("next")), "items": items})


@mcp.tool(annotations=READ)
async def onshape_get_document(did: str) -> str:
    """Get metadata for one document, including its default workspace id."""
    return await _run(client().get(f"/documents/{did}"))


@mcp.tool(annotations=WRITE)
async def onshape_create_document(name: str, description: str = "", is_public: bool = False) -> str:
    """Create a new Onshape document. Returns its id and default workspace id."""
    try:
        d = await client().post(
            "/documents", json={"name": name, "description": description, "isPublic": is_public}
        )
    except OnshapeError as e:
        return f"Error: {e}"
    return _dump(
        {
            "id": d.get("id"),
            "name": d.get("name"),
            "defaultWorkspaceId": (d.get("defaultWorkspace") or {}).get("id"),
            "href": f"{client().base_url}/documents/{d.get('id')}",
        }
    )


@mcp.tool(annotations=READ)
async def onshape_list_workspaces(did: str) -> str:
    """List workspaces (branches) of a document."""
    return await _run(client().get(f"/documents/d/{did}/workspaces"))


@mcp.tool(annotations=READ)
async def onshape_list_versions(did: str) -> str:
    """List named versions of a document."""
    return await _run(client().get(f"/documents/d/{did}/versions"))


@mcp.tool(annotations=WRITE)
async def onshape_create_version(did: str, workspace_id: str, name: str, description: str = "") -> str:
    """Create a named version (snapshot) of a workspace."""
    return await _run(
        client().post(
            f"/documents/d/{did}/versions",
            json={"documentId": did, "workspaceId": workspace_id, "name": name, "description": description},
        )
    )


@mcp.tool(annotations=READ)
async def onshape_list_elements(did: str, wvm: WVM, wvmid: str, element_type: str | None = None) -> str:
    """List the tabs (elements) in a document: Part Studios, Assemblies, Drawings, Variable Studios...
    element_type optionally filters, e.g. PARTSTUDIO, ASSEMBLY, DRAWING, VARIABLESTUDIO."""
    try:
        data = await client().get(f"/documents/d/{did}/{wvm}/{wvmid}/elements", params={"elementType": element_type})
    except OnshapeError as e:
        return f"Error: {e}"
    return _dump([{"id": e.get("id"), "name": e.get("name"), "type": e.get("elementType")} for e in data])


# --------------------------------------------------------------------------- part studios


@mcp.tool(annotations=WRITE)
async def onshape_create_part_studio(did: str, wid: str, name: str) -> str:
    """Create a new Part Studio tab in a workspace."""
    return await _run(client().post(f"/partstudios/d/{did}/w/{wid}", json={"name": name}))


@mcp.tool(annotations=READ)
async def onshape_list_parts(did: str, wvm: WVM, wvmid: str, eid: str) -> str:
    """List parts in a Part Studio (name, partId, material, appearance)."""
    try:
        data = await client().get(f"/parts{_p(did, wvm, wvmid, eid)}")
    except OnshapeError as e:
        return f"Error: {e}"
    return _dump(
        [
            {
                "name": p.get("name"),
                "partId": p.get("partId"),
                "bodyType": p.get("bodyType"),
                "material": (p.get("material") or {}).get("displayName"),
                "partNumber": p.get("partNumber"),
            }
            for p in data
        ]
    )


@mcp.tool(annotations=READ)
async def onshape_get_features(did: str, wvm: WVM, wvmid: str, eid: str) -> str:
    """Get the full feature list of a Part Studio as Onshape BTMFeature JSON.
    Useful as a template before calling onshape_add_feature."""
    return await _run(client().get(f"/partstudios{_p(did, wvm, wvmid, eid)}/features"))


@mcp.tool(annotations=WRITE)
async def onshape_add_feature(did: str, wid: str, eid: str, feature: dict[str, Any]) -> str:
    """Add a feature to a Part Studio (workspace only). `feature` is a BTMFeature-134 JSON object, e.g.
    {"btType": "BTMFeature-134", "featureType": "extrude", "name": "Extrude 1", "parameters": [...]}.
    Read an existing Part Studio with onshape_get_features to see the exact parameter shapes.
    Tips: sketches use btType "BTMSketch-151" with featureType "newSketch", a "sketchPlane" query
    (default plane deterministicIds: Top "JDC", Front "JCC", Right "JEC") and "entities"
    (e.g. BTMSketchCurve-4 + BTCurveGeometryCircle-115, lengths in meters). Extrude takes
    bodyType (enumName "ExtendedToolBodyType"), operationType ("NewBodyOperationType": NEW/ADD/REMOVE),
    entities (BTMIndividualSketchRegionQuery-140 with the sketch featureId), endBound ("BoundingType": BLIND)
    and depth (BTMParameterQuantity-147 expression like "30 mm"). See README for a full tested example.
    The response includes featureState - check it for errors (featureStatus != OK)."""
    return await _run(client().post(f"/partstudios/d/{did}/w/{wid}/e/{eid}/features", json={"feature": feature}))


@mcp.tool(annotations=WRITE)
async def onshape_update_feature(did: str, wid: str, eid: str, feature_id: str, feature: dict[str, Any]) -> str:
    """Replace an existing feature's definition (same BTMFeature JSON as onshape_add_feature, including featureId)."""
    return await _run(
        client().post(
            f"/partstudios/d/{did}/w/{wid}/e/{eid}/features/featureid/{feature_id}", json={"feature": feature}
        )
    )


@mcp.tool(annotations=DESTRUCTIVE)
async def onshape_delete_feature(did: str, wid: str, eid: str, feature_id: str) -> str:
    """Delete a feature from a Part Studio by feature id."""
    return await _run(client().delete(f"/partstudios/d/{did}/w/{wid}/e/{eid}/features/featureid/{feature_id}"))


@mcp.tool(annotations=READ)
async def onshape_eval_featurescript(
    did: str, wvm: WVM, wvmid: str, eid: str, script: str
) -> str:
    """Evaluate a FeatureScript lambda against a Part Studio and return the result. The script must be a
    function, e.g. `function(context is Context, queries) { return size(evaluateQuery(context, qAllModifiableSolidBodies())); }`"""
    return await _run(
        client().post(f"/partstudios{_p(did, wvm, wvmid, eid)}/featurescript", json={"script": script, "queries": {}})
    )


@mcp.tool(annotations=READ)
async def onshape_get_mass_properties(did: str, wvm: WVM, wvmid: str, eid: str, part_id: str | None = None) -> str:
    """Mass, volume, centroid and inertia of a Part Studio (or one part via part_id). Requires materials for mass."""
    return await _run(
        client().get(f"/partstudios{_p(did, wvm, wvmid, eid)}/massproperties", params={"partId": part_id})
    )


@mcp.tool(annotations=READ)
async def onshape_get_bounding_box(did: str, wvm: WVM, wvmid: str, eid: str) -> str:
    """Axis-aligned bounding box of all parts in a Part Studio (meters)."""
    return await _run(client().get(f"/partstudios{_p(did, wvm, wvmid, eid)}/boundingboxes"))


# --------------------------------------------------------------------------- assemblies


@mcp.tool(annotations=READ)
async def onshape_get_assembly(did: str, wvm: WVM, wvmid: str, eid: str) -> str:
    """Get an assembly definition: instances, sub-assemblies, occurrences/transforms and mates."""
    return await _run(
        client().get(f"/assemblies{_p(did, wvm, wvmid, eid)}", params={"includeMateFeatures": "true"})
    )


@mcp.tool(annotations=READ)
async def onshape_get_bom(did: str, wvm: WVM, wvmid: str, eid: str) -> str:
    """Get the Bill of Materials for an assembly."""
    return await _run(client().get(f"/assemblies{_p(did, wvm, wvmid, eid)}/bom"))


# --------------------------------------------------------------------------- variables


@mcp.tool(annotations=READ)
async def onshape_get_variables(did: str, wvm: WVM, wvmid: str, eid: str) -> str:
    """Get variables defined in a Variable Studio element."""
    return await _run(client().get(f"/variables{_p(did, wvm, wvmid, eid)}/variables"))


@mcp.tool(annotations=WRITE)
async def onshape_set_variables(did: str, wid: str, eid: str, variables: list[dict[str, Any]]) -> str:
    """Set variables in a Variable Studio (replaces the table). Each item:
    {"name": "width", "type": "LENGTH", "expression": "25 mm", "description": ""}.
    type is one of LENGTH, ANGLE, NUMBER, ANY."""
    return await _run(client().post(f"/variables/d/{did}/w/{wid}/e/{eid}/variables", json=variables))


@mcp.tool(annotations=WRITE)
async def onshape_create_variable_studio(did: str, wid: str, name: str) -> str:
    """Create a new Variable Studio tab in a workspace. Returns its element id (use with onshape_set_variables)."""
    try:
        r = await client().post(f"/variables/d/{did}/w/{wid}/variablestudio", json={"name": name})
    except OnshapeError as e:
        return f"Error: {e}"
    return _dump({"id": r.get("id"), "name": r.get("name"), "type": r.get("elementType")})


# --------------------------------------------------------------------------- visuals & export


@mcp.tool(annotations=READ)
async def onshape_get_shaded_view(
    did: str,
    wvm: WVM,
    wvmid: str,
    eid: str,
    element_kind: Literal["partstudio", "assembly"] = "partstudio",
    view: str = "isometric",
    width: int = 800,
    height: int = 600,
) -> Image | str:
    """Render a shaded PNG image of a Part Studio or Assembly so you can see the model.
    view: isometric, front, back, top, bottom, left, right, or a 12-number view matrix string."""
    base = "/partstudios" if element_kind == "partstudio" else "/assemblies"
    try:
        data = await client().get(
            f"{base}{_p(did, wvm, wvmid, eid)}/shadedviews",
            params={"viewMatrix": view, "outputWidth": width, "outputHeight": height, "pixelSize": 0},
        )
    except OnshapeError as e:
        return f"Error: {e}"
    images = data.get("images") or []
    if not images:
        return "Error: Onshape returned no image (the element may be empty)."
    return Image(data=base64.b64decode(images[0]), format="png")


@mcp.tool(annotations=WRITE)
async def onshape_export_stl(
    did: str,
    wvm: WVM,
    wvmid: str,
    eid: str,
    output_path: str,
    part_id: str | None = None,
    units: Literal["millimeter", "centimeter", "meter", "inch", "foot"] = "millimeter",
) -> str:
    """Export a Part Studio (or a single part) as binary STL and save it to output_path on this machine."""
    try:
        resp = await client().request_raw(
            "GET",
            f"/partstudios{_p(did, wvm, wvmid, eid)}/stl",
            params={"mode": "binary", "units": units, "grouping": "true", "partIds": part_id},
            accept="application/vnd.onshape.v1+octet-stream",
        )
    except OnshapeError as e:
        return f"Error: {e}"
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(resp.content)
    return f"Saved {len(resp.content)} bytes to {out}"


# --------------------------------------------------------------------------- escape hatch


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=True))
async def onshape_api_request(
    method: Literal["GET", "POST", "DELETE"],
    path: str,
    query: dict[str, Any] | None = None,
    body: Any = None,
) -> str:
    """Call any Onshape REST endpoint directly, for anything the other tools don't cover.
    path is relative to /api/v10, e.g. "/documents/d/<did>/w/<wid>/elements" (or pass a full /api/vX/... path).
    See https://cad.onshape.com/glassworks/explorer for the full API."""
    return await _run(client().request(method, path, params=query, json=body))


async def _check() -> int:
    """Verify credentials by calling Onshape once. Returns a process exit code."""
    try:
        info = await client().get("/users/sessioninfo")
    except OnshapeError as e:
        print(f"FAILED: {e}")
        return 1
    # Onshape answers sessioninfo with an empty 204 (not 401) when the keys are wrong.
    if not isinstance(info, dict) or not info.get("id"):
        print(
            "FAILED: Onshape did not accept these API keys. Check ONSHAPE_ACCESS_KEY / ONSHAPE_SECRET_KEY "
            "(create new ones at https://dev-portal.onshape.com/keys)."
        )
        return 1
    print(f"OK - connected to {client().base_url} as {info.get('name') or info.get('email') or 'unknown user'}")
    return 0


def main() -> None:
    import argparse
    import asyncio
    import logging
    import sys

    from . import __version__

    parser = argparse.ArgumentParser(prog="onshape-mcp", description="MCP server for Onshape (stdio).")
    parser.add_argument("--check", action="store_true", help="test your Onshape API keys and exit")
    parser.add_argument("--version", action="version", version=f"onshape-mcp {__version__}")
    args = parser.parse_args()

    logging.getLogger("httpx").setLevel(logging.WARNING)
    if args.check:
        sys.exit(asyncio.run(_check()))
    if not os.environ.get("ONSHAPE_ACCESS_KEY"):
        print("Warning: ONSHAPE_ACCESS_KEY not set; tools will return an auth error.", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
