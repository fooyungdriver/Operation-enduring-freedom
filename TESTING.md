# Testing before you deploy

This app touches three things that are risky to get wrong: your **live Zoho
data**, **pre-printed manifest forms** (you don't want to waste a stack), and the
**Claude API** (it costs money per call). Test each in isolation first, then do
one full dress rehearsal on a single PC before rolling the app out to the others.

There are four layers, cheapest/safest first.

## Layer 1 — Automated tests (run every time, no setup)

These run entirely offline: Zoho and Claude are mocked, and printing writes to a
file instead of a printer. Nothing here can touch production data or a printer.

```
pip install -r requirements.txt
pytest
```

You should see all tests pass. Run this after any change and before every
deploy. The tests cover: manifest/LDR rendering, the Zoho-record → manifest
mapping, calibration math, config/env handling, and every web page (including
the print action and the "not configured" fallbacks).

## Layer 2 — Print layout, without wasting forms

Goal: confirm fields land in the right boxes **before** loading a real form.

1. Run the app (`start.bat` / `./start.sh`) and open a generator → **Print
   manifest**. The on-screen **preview** is a character-accurate map of where
   text will print.
2. With no printer name set (or on a Mac/Linux machine), clicking **Print**
   writes a `.prn` file into `out/`. Open it in a text editor to inspect the
   exact layout.
3. Print that `.prn` (or the preview) onto **plain paper**, then hold it against
   a blank pre-printed form on a window — you'll see how close the alignment is.
4. Use the **Calibration** screen: print the test pattern onto **one** real form,
   read how far off the markers are, adjust the X/Y offset, save, repeat. One
   sacrificial form is all it should take.
5. If whole boxes are in the wrong place (not just a global shift), adjust
   `FIELD_POS` / `LINE_ITEM` in `app/printing/manifest_8700_22.py`.

## Layer 3 — Zoho, against test data (not production)

Pick one:

**Option A — Zoho CRM Sandbox (recommended).** Zoho One Enterprise includes a
CRM Sandbox. In Zoho Developer Hub, create/refresh the sandbox, generate a
refresh token scoped to it, and in `config.json` set `zoho.api_host_override` to
the sandbox API host plus that sandbox refresh token. The app then reads/writes
the sandbox only — production is never touched. Clear the override to go live.

**Option B — Tagged test records in production.** If you don't use a sandbox,
create a few generators/profiles named `TEST – …` and only act on those during
testing. Lower effort, but be careful not to print/log against real customers.

What to verify in Zoho:
- The generator list loads and search works.
- A generator's profiles and lab packs show up (confirms the lookup field names
  match — if a list is empty but shouldn't be, the field name in
  `app/zoho_client.py` / `manifest_builder.py` needs adjusting to your CRM).
- Printing a manifest creates a `Manifest_Log` record (check it appears in Zoho).

## Layer 4 — Claude skills (cheap, but real API calls)

Add your Anthropic API key, then:
- **Profile from SDS:** paste a known SDS and confirm the structured draft looks
  right and flags uncertain items under "needs review."
- **Suggest waste codes:** give a waste you already know the codes for and check
  the suggestions and confidence levels.
- **Manifest check:** deliberately leave out an EPA ID / UN number and confirm it
  gets flagged.

Treat all skill output as a **draft to verify** — that's by design.

## The pre-deployment dress rehearsal (one PC)

Before installing on all the ops PCs, do a full run on one machine connected to
the real dot-matrix printer:

- [ ] `pytest` is green.
- [ ] Config points at the **sandbox** (or only tagged TEST records).
- [ ] Calibration is dialed in; the test pattern lands on the boxes.
- [ ] Print one full manifest onto a real form end-to-end and eyeball every box.
- [ ] A `Manifest_Log` record was created in Zoho.
- [ ] LDR prints correctly.
- [ ] Each Claude skill returns sensible output.
- [ ] Switch config to **production** (clear `api_host_override`, use the
      production refresh token) and re-print one form to confirm the live data
      flows. Then roll the `dist/` build + `config.json` out to the other PCs.

## Tip: catch regressions automatically

If you'd like `pytest` to run automatically at the start of each Claude Code web
session (so the project is always verified before changes), ask and I'll add a
SessionStart hook for it.
