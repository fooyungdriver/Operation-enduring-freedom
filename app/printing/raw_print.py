"""Send raw bytes to a printer (dot-matrix), bypassing the driver.

For overprinting pre-printed forms we must send ESC/P bytes verbatim so the
printer positions text exactly — Windows print *drivers* would re-render and
ruin alignment. ``win32print`` with datatype ``RAW`` writes straight to the
spooler.

On macOS/Linux dev machines (where ``pywin32`` isn't installed) and whenever no
printer name is configured, we fall back to writing the bytes to a ``.prn`` file
under ``out/``. That makes the whole pipeline runnable and testable without a
physical printer, and the ``.prn`` can later be copied to a printer with
``copy /b file.prn \\\\computer\\printer`` on Windows.
"""

from __future__ import annotations

import time
from pathlib import Path

from ..config import OUT_DIR

try:  # Windows only
    import win32print  # type: ignore

    _HAVE_WIN32 = True
except Exception:
    _HAVE_WIN32 = False


def have_real_printing() -> bool:
    return _HAVE_WIN32


def list_printers() -> list[str]:
    """Return installed Windows printer names (empty list off-Windows)."""
    if not _HAVE_WIN32:
        return []
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [p[2] for p in win32print.EnumPrinters(flags)]


def send_raw(data: bytes, *, printer_name: str | None, job_name: str) -> str:
    """Send ``data`` to ``printer_name``. Returns a human-readable destination.

    Falls back to a ``.prn`` file when real printing is unavailable or no
    printer is configured.
    """
    if _HAVE_WIN32 and printer_name:
        handle = win32print.OpenPrinter(printer_name)
        try:
            # ("doc name", output_file=None, datatype="RAW")
            win32print.StartDocPrinter(handle, 1, (job_name, None, "RAW"))
            try:
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, data)
                win32print.EndPagePrinter(handle)
            finally:
                win32print.EndDocPrinter(handle)
        finally:
            win32print.ClosePrinter(handle)
        return f"printer '{printer_name}'"

    # Fallback: write a .prn file.
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in job_name)
    path: Path = OUT_DIR / f"{safe}_{int(time.time())}.prn"
    path.write_bytes(data)
    reason = "no printer configured" if _HAVE_WIN32 else "raw printing unavailable on this OS"
    return f"file '{path}' ({reason})"
