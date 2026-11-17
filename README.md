# Onshape MCP

<!-- mcp-name: io.github.AnasShaheen2012/onshape-mcp -->

[![CI](https://github.com/AnasShaheen2012/onshape-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/AnasShaheen2012/onshape-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/AnasShaheen2012/onshape-mcp?style=social)](https://github.com/AnasShaheen2012/onshape-mcp/stargazers)

**Talk to your CAD.** Connect **Claude** (or any [MCP](https://modelcontextprotocol.io) client) to your **Onshape** CAD account. Ask in plain English and Claude can:

- 🔎 find your documents and look inside Part Studios and Assemblies
- 🖼️ **see** your model (renders a shaded image Claude can look at)
- ✏️ create documents, sketches and extrudes, and edit or delete features
- 📐 read mass properties, bounding boxes, BOMs and variables
- 💾 export STL files for 3D printing
- 🧪 run FeatureScript, or call any Onshape REST endpoint

Works with free, Education (student) and paid Onshape accounts.

> Example: *"Here's my Part Studio link: … Show me an isometric view, then make the bracket 5 mm thicker and export it as STL to my Desktop."*

### Why this one?

- **5-minute setup**: one command, no cloning and no Python to manage.
- **`--check` tells you exactly what's wrong**: bad key, missing key, or no permission on a document.
- **Claude can actually see your model**: it renders shaded views and looks at them before and after edits.
- **Made for robotics teams and students**: tested on real FTC robot CAD, with free and Education accounts treated as first-class.
- **Small and readable**: two Python files you can audit in 10 minutes. Your keys never leave your machine except to talk to Onshape.

---

## Setup (about 5 minutes)

### Step 1 — Get Onshape API keys

1. Sign in at **https://dev-portal.onshape.com/keys** with your normal Onshape login.
2. Click **Create new API key** and tick these scopes:
   - `OAuth2Read` — required
   - `OAuth2Write` — to create and edit
   - `OAuth2Delete` — to delete features
3. Copy the **Access key** and **Secret key**. The secret is shown only once.

> Keep these private. Anyone with them can access your Onshape account. If one leaks, delete it in the dev portal and make a new one.

### Step 2 — Install `uv`

[`uv`](https://docs.astral.sh/uv/) downloads and runs this server automatically, so you don't need to manage Python yourself.

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen your terminal afterwards.

### Step 3 — Add it to Claude

#### Option A: Claude Code (CLI or desktop app)

Run this once in a terminal, pasting your own keys:

```bash
claude mcp add onshape --scope user -e ONSHAPE_ACCESS_KEY=YOUR_ACCESS_KEY -e ONSHAPE_SECRET_KEY=YOUR_SECRET_KEY -- uvx --from git+https://github.com/AnasShaheen2012/onshape-mcp onshape-mcp
```

Then start a new Claude Code session.

#### Option B: Claude Desktop (chat app)

1. Open Claude Desktop → **Settings → Developer → Edit Config**. This opens `claude_desktop_config.json`.
2. Paste the following, with your own keys. If the file already has `mcpServers`, add just the `"onshape"` block inside it.

```json
{
  "mcpServers": {
    "onshape": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/AnasShaheen2012/onshape-mcp", "onshape-mcp"],
      "env": {
        "ONSHAPE_ACCESS_KEY": "YOUR_ACCESS_KEY",
        "ONSHAPE_SECRET_KEY": "YOUR_SECRET_KEY"
      }
    }
  }
}
```

3. **Fully quit** Claude Desktop and reopen it. On Windows that means right-clicking the tray icon and choosing Quit. On macOS, press Cmd+Q.

> **macOS:** if Claude Desktop says it can't find `uvx`, replace `"uvx"` with its full path. Run `which uvx` in Terminal to get it; it's usually `/Users/<you>/.local/bin/uvx`.

#### Other MCP clients (Cursor, VS Code, Windsurf, …)

Use the same command and env as in Option B: command `uvx`, args `--from git+https://github.com/AnasShaheen2012/onshape-mcp onshape-mcp`.

### Step 4 — Try it

Ask Claude:

> List my 5 most recent Onshape documents.

If you see your documents, you're done. 🎉

> The very first start takes 10–20 seconds while `uv` downloads the server; after that it starts instantly from cache.

---

## Things to ask Claude

- "Show me what's in this document: `<paste Onshape URL>`"
- "Render an isometric view of the Part Studio and tell me its overall dimensions."
- "Create a new document called *Test* with a 40 mm × 20 mm cylinder."
- "What's the mass of each part? Use aluminum 6061 if no material is set."
- "Set the `wall_thickness` variable to 3 mm."
- "Export this Part Studio as STL to my Downloads folder."
- "Save a version called *before-changes*."

Tip: paste the URL straight from your browser. Claude pulls the document, workspace and tab IDs out of it automatically.

---

## Tools

| Area | Tools |
|---|---|
| Helpers | `onshape_parse_url` |
| Documents | `onshape_search_documents`, `onshape_get_document`, `onshape_create_document`, `onshape_list_workspaces`, `onshape_list_versions`, `onshape_create_version`, `onshape_list_elements` |
| Part Studios | `onshape_create_part_studio`, `onshape_list_parts`, `onshape_get_features`, `onshape_add_feature`, `onshape_update_feature`, `onshape_delete_feature`, `onshape_eval_featurescript`, `onshape_get_mass_properties`, `onshape_get_bounding_box` |
| Assemblies | `onshape_get_assembly`, `onshape_get_bom` |
| Variables | `onshape_create_variable_studio`, `onshape_get_variables`, `onshape_set_variables` |
| Visuals / export | `onshape_get_shaded_view` (PNG Claude can see), `onshape_export_stl` |
| Anything else | `onshape_api_request`: a raw call to any endpoint in the [Onshape API explorer](https://cad.onshape.com/glassworks/explorer) |

Most tools take `did` (document), `wvm` (`w` workspace / `v` version / `m` microversion), `wvmid` and `eid` (tab). Edits need `wvm = w`, because versions are read-only.

---

## Troubleshooting

**Check your keys from a terminal.** On macOS / Linux:

```bash
ONSHAPE_ACCESS_KEY=YOUR_ACCESS_KEY ONSHAPE_SECRET_KEY=YOUR_SECRET_KEY uvx --from git+https://github.com/AnasShaheen2012/onshape-mcp onshape-mcp --check
```

Windows PowerShell:

```powershell
$env:ONSHAPE_ACCESS_KEY="YOUR_ACCESS_KEY"; $env:ONSHAPE_SECRET_KEY="YOUR_SECRET_KEY"; uvx --from git+https://github.com/AnasShaheen2012/onshape-mcp onshape-mcp --check
```

It prints `OK - connected to … as <your name>` or explains what's wrong.

| Problem | Fix |
|---|---|
| `Missing Onshape credentials` | The keys aren't reaching the server. Check the `env` block in your config, then fully restart the app. |
| `HTTP 401` | The key is wrong or was deleted. Make a new one in the dev portal. |
| `HTTP 403` on edit or export | You only have view access to that document, e.g. a team document shared read-only. Use a document you own, or ask the owner for Edit/Export permission. |
| `HTTP 429` | Rate limited. Wait a bit. Onshape also caps yearly API calls per plan; check usage in the dev portal. |
| Server doesn't appear in Claude | Make sure `uvx --version` works in a terminal, then fully quit and reopen Claude. If you installed `uv` while Claude was open, Claude won't see it until it restarts. |
| Server shows as "failed" the first time | The first launch downloads the server and can exceed the client's startup timeout. Run the `--check` command above once to pre-download it, then restart Claude. |
| Enterprise account | Add `ONSHAPE_BASE_URL=https://yourcompany.onshape.com` to `env`. |

---

## Advanced

<details>
<summary>Install with pip instead of uv</summary>

```bash
pip install git+https://github.com/AnasShaheen2012/onshape-mcp
```

Then use `onshape-mcp` as the command in your MCP config, with no args.
</details>

<details>
<summary>Develop locally</summary>

```bash
git clone https://github.com/AnasShaheen2012/onshape-mcp
cd onshape-mcp
python -m venv .venv
.venv/bin/pip install -e ".[dev]"    # Windows: .venv\Scripts\pip install -e ".[dev]"
pytest
```

Test interactively with the MCP Inspector: `npx @modelcontextprotocol/inspector .venv/bin/onshape-mcp`.
</details>

<details>
<summary>Feature JSON example (sketch + extrude)</summary>

`onshape_add_feature` takes Onshape's raw feature JSON. Claude usually figures it out, especially if you let it read an existing feature first with `onshape_get_features`. Here's a tested example that makes a 20 mm diameter, 30 mm tall cylinder.

Sketch on the Top plane. Lengths are in meters. The default plane IDs are Top `JDC`, Front `JCC` and Right `JEC`.

```json
{"btType": "BTMSketch-151", "featureType": "newSketch", "name": "Sketch circle",
 "parameters": [{"btType": "BTMParameterQueryList-148", "parameterId": "sketchPlane",
   "queries": [{"btType": "BTMIndividualQuery-138", "deterministicIds": ["JDC"]}]}],
 "entities": [{"btType": "BTMSketchCurve-4", "entityId": "circle1",
   "geometry": {"btType": "BTCurveGeometryCircle-115", "radius": 0.01, "xCenter": 0, "yCenter": 0,
                "xDir": 1, "yDir": 0, "clockwise": false}}],
 "constraints": []}
```

Extrude it. Use the sketch's `featureId` from the add response:

```json
{"btType": "BTMFeature-134", "featureType": "extrude", "name": "Extrude cylinder",
 "parameters": [
  {"btType": "BTMParameterEnum-145", "parameterId": "bodyType", "enumName": "ExtendedToolBodyType", "value": "SOLID", "namespace": ""},
  {"btType": "BTMParameterEnum-145", "parameterId": "operationType", "enumName": "NewBodyOperationType", "value": "NEW", "namespace": ""},
  {"btType": "BTMParameterQueryList-148", "parameterId": "entities",
   "queries": [{"btType": "BTMIndividualSketchRegionQuery-140", "featureId": "<sketch featureId>"}]},
  {"btType": "BTMParameterEnum-145", "parameterId": "endBound", "enumName": "BoundingType", "value": "BLIND", "namespace": ""},
  {"btType": "BTMParameterQuantity-147", "parameterId": "depth", "expression": "30 mm", "isInteger": false}]}
```
</details>

---

## Security & privacy

- Your keys stay on your machine. They're read from environment variables and sent only to Onshape over HTTPS, using API-key Basic auth.
- This server talks only to Onshape (`cad.onshape.com`, or your `ONSHAPE_BASE_URL`).
- Claude can edit and delete features in documents you have edit rights to. Onshape keeps full history, so you can always restore earlier states, and saving a version before big changes is a good habit.

## Contributing

Issues and pull requests are welcome, especially new tools such as assembly editing, drawings, STEP export or configurations. Run `pytest` before opening a PR.

## License

MIT. This is a community project and isn't affiliated with or endorsed by Onshape or PTC.

---

⭐ **If this saved you time, star the repo.** It helps other Onshape users find it.
