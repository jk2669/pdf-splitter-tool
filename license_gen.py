"""
License Generator — run this to create a new license.lic file.

Usage:
    python license_gen.py <machine_id> <expires YYYY-MM-DD> [output_path]

Example:
    python license_gen.py 89937493-95e6-4d0f-ad11-6186600b86b4 2026-09-11
    python license_gen.py 89937493-95e6-4d0f-ad11-6186600b86b4 2026-09-11 C:/Licenses/license.lic
"""

import hashlib
import hmac
import json
import sys
from pathlib import Path

_SECRET = b"PdfSplit$2026!SecureKey#8f3a"


def _sign(machine_id: str, expires: str) -> str:
    msg = f"{machine_id.lower()}|{expires}".encode()
    return hmac.new(_SECRET, msg, hashlib.sha256).hexdigest()


def generate(machine_id: str, expires: str, output: str = "license.lic") -> None:
    sig = _sign(machine_id.lower(), expires)
    lic = {
        "machine_id": machine_id.lower(),
        "expires":    expires,
        "sig":        sig,
    }
    out = Path(output)
    out.write_text(json.dumps(lic, indent=2), encoding="utf-8")
    print(f"License written to: {out.resolve()}")
    print(f"  Machine ID : {machine_id}")
    print(f"  Expires    : {expires}")
    print(f"  Signature  : {sig}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    mid  = sys.argv[1]
    exp  = sys.argv[2]
    dest = sys.argv[3] if len(sys.argv) >= 4 else "license.lic"
    generate(mid, exp, dest)
