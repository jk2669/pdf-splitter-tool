"""
License verification for PDF Document Splitter.
Checks machine ID binding and expiry on every launch.
"""

import hashlib
import hmac
import json
import sys
from datetime import date
from pathlib import Path

# Embedded signing secret — must match license_gen.py
_SECRET = b"PdfSplit$2026!SecureKey#8f3a"


def _sign(machine_id: str, expires: str) -> str:
    msg = f"{machine_id.lower()}|{expires}".encode()
    return hmac.new(_SECRET, msg, hashlib.sha256).hexdigest()


def _get_machine_id() -> str:
    """Read the Windows MachineGuid from the registry."""
    if sys.platform != "win32":
        return "dev"   # bypass on macOS/Linux dev machines
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        ) as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return value.lower()
    except Exception:
        return ""


def _lic_path() -> Path:
    """License file lives next to the exe (or script during development)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "license.lic"
    return Path(__file__).parent / "license.lic"


def verify() -> tuple[bool, str]:
    """
    Returns (ok: bool, message: str).
    Call at application startup; show the message and exit if not ok.
    """
    path = _lic_path()

    if not path.exists():
        return False, (
            "License file not found.\n\n"
            f"Expected: {path}\n\n"
            "Please place license.lic next to the application."
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        lic_machine = data["machine_id"]
        expires     = data["expires"]
        sig         = data["sig"]
    except Exception:
        return False, "License file is corrupted or has an invalid format."

    # 1 — Signature check (tamper detection)
    expected = _sign(lic_machine, expires)
    if not hmac.compare_digest(sig, expected):
        return False, "License file has been tampered with."

    # 2 — Machine binding
    current = _get_machine_id()
    if current not in ("dev", "") and current != lic_machine.lower():
        return False, (
            "This license is not valid for this machine.\n\n"
            "Please contact support to obtain a new license."
        )

    # 3 — Expiry
    try:
        expiry = date.fromisoformat(expires)
    except ValueError:
        return False, "License contains an invalid expiry date."

    today = date.today()
    if today > expiry:
        return False, (
            f"License expired on {expires}.\n\n"
            "Please contact support to renew your license."
        )

    days_left = (expiry - today).days
    return True, f"Licensed until {expires} · {days_left} day(s) remaining"
