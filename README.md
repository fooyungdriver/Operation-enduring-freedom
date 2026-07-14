# Red Arc Environmental — Ops Tool

A lightweight internal tool for Red Arc Environmental, Inc.'s hazardous-waste
operations. It reads **generators, waste profiles and lab pack inventory** from
**Zoho CRM**, prints **Uniform Hazardous Waste Manifests (EPA Form 8700-22)** and
**LDR** documents onto a **dot-matrix printer** using pre-printed forms, and offers
**Claude-powered helpers** (draft a profile from an SDS, suggest waste codes, check
a manifest).

> **Where things live:** Zoho CRM is the single source of truth (your data, your
> logins, your backups — nothing extra to host). This app runs **locally on each
> ops PC** because driving a dot-matrix printer for overprinting must happen on the
> machine the printer is attached to.

## What's here (Phase 1 / MVP)

```
app/
  config.py              # loads config.json / env vars
  zoho_client.py         # Zoho CRM v8 client (OAuth refresh, records)
  manifest_builder.py    # Zoho records -> printable ManifestData
  server.py              # Flask app (the browser UI)
  printing/
    escp.py              # ESC/P codes + fixed-width page grid
    raw_print.py         # RAW printing on Windows; .prn fallback elsewhere
    manifest_8700_22.py  # manifest data model + renderer
    ldr.py               # LDR document
    calibration.py       # alignment test pattern
  skills/                # Claude skills (profile-from-SDS, waste codes, manifest check)
  templates/ static/     # the UI
```

## Setup

1. **Install Python 3.10+** (on Windows, the "py" launcher is fine).
2. **Install dependencies:** `pip install -r requirements.txt`
   (`pywin32` installs only on Windows; on Mac/Linux the app prints to `.prn`
   files in `out/` instead of a real printer.)
3. **Create your config:** copy `config.example.json` to `config.json` and fill it
   in. `config.json` is git-ignored and never committed. Any value can instead be
   supplied as an environment variable (e.g. `ANTHROPIC_API_KEY`,
   `ZOHO_CLIENT_ID`), which takes priority.
4. **Run it:** double-click `start.bat` (Windows) or run `./start.sh`
   (Mac/Linux), then open <http://127.0.0.1:5000>.

### Zoho one-time setup (refresh token)

1. In the Zoho API console (<https://api-console.zoho.com>), create a
   **Self Client**.
2. Generate a grant token with scope
   `ZohoCRM.modules.ALL,ZohoCRM.settings.READ`.
3. Exchange the grant token for a **refresh token** (one `curl`/Postman call to
   `https://accounts.zoho.com/oauth/v2/token`). Put the `client_id`,
   `client_secret`, and `refresh_token` into `config.json`. Set `data_center` to
   match your account (`com`, `eu`, `in`, `com.au`, `jp`).

The app refreshes short-lived access tokens automatically from there.

### Zoho modules used

* **`Generators`** — already exists in Red Arc's CRM (the app reuses it).
* **`Waste_Profiles`**, **`Lab_Pack_Inventory`**, **`Manifest_Log`** — create these
  as custom modules in the Zoho CRM UI. The app reads/writes records but does not
  create modules. Confirm the exact field API names during setup and adjust
  `manifest_builder.py` / the skills if your field names differ.

## Printing & calibration

Overprinting pre-printed forms means only the variable data prints, landing in the
form's boxes. To line it up:

1. Set the printer name(s) in `config.json` (`printing.manifest_printer_name`,
   `ldr_printer_name`). Names of detected printers appear on the **Settings** page.
2. Open **Calibration**, print the test pattern onto **one** pre-printed form, and
   nudge the X/Y offset until the markers sit on the boxes. Offsets are saved and
   applied to every print.
3. If the box positions themselves need adjusting, edit `FIELD_POS` / `LINE_ITEM`
   in `app/printing/manifest_8700_22.py`.

On non-Windows machines (or with no printer name set), prints are written to
`out/*.prn` so you can develop and verify the layout without a printer.

## Testing before deployment

Run the automated suite (offline — Zoho/Claude mocked, printing to file):

```
pip install -r requirements.txt
pytest
```

See **[TESTING.md](TESTING.md)** for the full pre-deployment plan: testing print
layout without wasting forms, using a Zoho **sandbox** (`zoho.api_host_override`)
instead of production, exercising the Claude skills, and the single-PC dress
rehearsal checklist before rolling out to the other machines.

## Claude skills

Configured with the official Anthropic SDK and model `claude-opus-4-8`. Each skill
is a single review-before-save helper — it never writes to Zoho on its own. Add
your Anthropic API key to `config.json` to enable them.

## Packaging for the other PCs (optional)

Build a one-folder Windows app so non-technical staff just double-click:

```
pyinstaller --name RedArcOps --add-data "app/templates;app/templates" ^
  --add-data "app/static;app/static" app/server.py
```

Ship the `dist/RedArcOps` folder plus a `config.json` to each printing PC.

## Roadmap (Phase 2+)

* **EPA e-Manifest (RCRAInfo API)** submission — the `ManifestData` model is the
  seam; add an `app/printing/emanifest.py` that submits the same object.
* **Client portal** — recommend Zoho's built-in Client Portal / Creator over a
  custom build (least to host and secure).
* Packaging polish / auto-update across the ops PCs.
