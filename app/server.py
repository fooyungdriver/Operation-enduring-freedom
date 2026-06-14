"""Flask app for the Red Arc Ops Tool.

Runs locally on an ops PC, serving a simple browser UI on 127.0.0.1. It reads
generators / profiles from Zoho, assembles and prints manifests + LDRs to the
locally-attached dot-matrix printer, and exposes the Claude skills.

Run with:  python -m app.server   (or the start.bat / start.sh helper)
"""

from __future__ import annotations

from typing import Any

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from .config import config
from .manifest_builder import build_manifest
from .printing import calibration as calib
from .printing import ldr as ldr_doc
from .printing import manifest_8700_22 as manifest_doc
from .printing.raw_print import have_real_printing, list_printers, send_raw
from .skills._client import SkillError
from .zoho_client import ZohoError, zoho

app = Flask(__name__)
app.secret_key = "red-arc-local-ops"  # local-only app; not exposed to the internet


# --- Helpers -------------------------------------------------------------

def _calib(doc_type: str) -> dict[str, int]:
    c = config.get("printing", "calibration", doc_type, default={}) or {}
    return {
        "x_offset_chars": int(c.get("x_offset_chars", 0)),
        "y_offset_lines": int(c.get("y_offset_lines", 0)),
        "cpi": int(c.get("cpi", 10)),
        "lpi": int(c.get("lpi", 6)),
    }


def _printer(doc_type: str) -> str | None:
    return config.get("printing", f"{doc_type}_printer_name") or None


@app.context_processor
def inject_status() -> dict[str, Any]:
    return {
        "zoho_ready": config.zoho_ready(),
        "anthropic_ready": config.anthropic_ready(),
        "real_printing": have_real_printing(),
    }


# --- Pages ---------------------------------------------------------------

@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/generators")
def generators() -> str:
    query = request.args.get("q", "").strip()
    rows: list[dict[str, Any]] = []
    error = None
    try:
        rows = zoho.search_generators(query) if query else zoho.list_generators()
    except ZohoError as exc:
        error = str(exc)
    return render_template("generators.html", generators=rows, q=query, error=error)


@app.route("/generators/<gen_id>")
def generator_detail(gen_id: str) -> str:
    error = None
    generator = None
    profiles: list[dict[str, Any]] = []
    try:
        generator = zoho.get_generator(gen_id)
        if generator is None:
            abort(404)
        profiles = zoho.list_profiles_for_generator(gen_id)
    except ZohoError as exc:
        error = str(exc)
    return render_template(
        "generator_detail.html",
        generator=generator,
        profiles=profiles,
        error=error,
    )


@app.route("/print/manifest/<gen_id>", methods=["GET", "POST"])
def print_manifest(gen_id: str):
    try:
        generator = zoho.get_generator(gen_id)
        if generator is None:
            abort(404)
        profiles = zoho.list_profiles_for_generator(gen_id)
    except ZohoError as exc:
        flash(str(exc), "error")
        return redirect(url_for("generators"))

    tracking = request.values.get("tracking_number", "").strip()
    selected_ids = set(request.form.getlist("profile_ids"))
    chosen = [p for p in profiles if str(p.get("id")) in selected_ids] or profiles
    data = build_manifest(generator, chosen, tracking_number=tracking)

    if request.method == "POST" and request.form.get("action") == "print":
        c = _calib("manifest")
        payload = manifest_doc.render_manifest(
            data,
            cpi=c["cpi"],
            lpi=c["lpi"],
            x_offset_chars=c["x_offset_chars"],
            y_offset_lines=c["y_offset_lines"],
        )
        dest = send_raw(
            payload,
            printer_name=_printer("manifest"),
            job_name=f"manifest_{tracking or gen_id}",
        )
        # Best-effort audit log to Zoho; don't fail the print if logging fails.
        log_status = "skipped (Zoho not configured)"
        if config.zoho_ready():
            try:
                zoho.create_manifest_log(
                    {
                        "Name": tracking or f"Manifest {generator.get('Name', '')}",
                        "Generator": {"id": gen_id},
                        "Tracking_Number": tracking,
                    }
                )
                log_status = "logged to Zoho Manifest_Log"
            except ZohoError as exc:
                log_status = f"log failed: {exc}"
        flash(f"Manifest sent to {dest}. {log_status}.", "ok")
        return redirect(url_for("generator_detail", gen_id=gen_id))

    return render_template(
        "print_manifest.html",
        generator=generator,
        profiles=profiles,
        data=data,
        preview=manifest_doc.preview_text(data),
        tracking_number=tracking,
    )


@app.route("/calibration", methods=["GET", "POST"])
def calibration():
    doc_type = request.values.get("doc_type", "manifest")
    if doc_type not in ("manifest", "ldr"):
        doc_type = "manifest"

    if request.method == "POST":
        action = request.form.get("action")
        offsets = {
            "x_offset_chars": int(request.form.get("x_offset_chars", 0) or 0),
            "y_offset_lines": int(request.form.get("y_offset_lines", 0) or 0),
            "cpi": int(request.form.get("cpi", 10) or 10),
            "lpi": int(request.form.get("lpi", 6) or 6),
        }
        if action == "save":
            config.save_printing_calibration(doc_type, offsets)
            flash("Calibration saved.", "ok")
        elif action == "test":
            payload = calib.render(**offsets)
            dest = send_raw(
                payload, printer_name=_printer(doc_type), job_name="calibration_test"
            )
            flash(f"Test pattern sent to {dest}.", "ok")
        return redirect(url_for("calibration", doc_type=doc_type))

    return render_template(
        "calibration.html",
        doc_type=doc_type,
        offsets=_calib(doc_type),
        preview=calib.preview_text(),
    )


@app.route("/settings")
def settings() -> str:
    return render_template(
        "settings.html",
        printers=list_printers(),
        data_center=config.zoho_data_center,
        model=config.anthropic_model,
    )


# --- Skills (each renders a form on GET, runs on POST) -------------------

@app.route("/skills/profile-from-sds", methods=["GET", "POST"])
def skill_profile_from_sds():
    result = None
    error = None
    text = request.form.get("text", "")
    if request.method == "POST":
        from .skills.profile_from_sds import draft_profile

        try:
            result = draft_profile(text)
        except SkillError as exc:
            error = str(exc)
    return render_template(
        "skill_profile.html", result=result, error=error, text=text
    )


@app.route("/skills/waste-codes", methods=["GET", "POST"])
def skill_waste_codes():
    result = None
    error = None
    facts = request.form.get("facts", "")
    state = request.form.get("state", "")
    if request.method == "POST":
        from .skills.waste_codes import suggest_codes

        try:
            result = suggest_codes(facts, state=state or None)
        except SkillError as exc:
            error = str(exc)
    return render_template(
        "skill_codes.html", result=result, error=error, facts=facts, state=state
    )


def main() -> None:
    app.run(host=config.server_host, port=config.server_port, debug=False)


if __name__ == "__main__":
    main()
