"""
PDF Document Splitter
=====================
Automatically splits a multi-page candidate PDF into separate files:
  - <number>.jpg           → Photo (page 1)
  - <number>_aadhaar.pdf  → Aadhaar card (page 2)
  - <number>_10th.pdf     → 10th marksheet (page 3)
  - <number>_12th.pdf     → 12th marksheet (page 4)

Usage:
    python pdf_splitter.py <path_to_pdf> [output_folder]

Example:
    python pdf_splitter.py "C:/Documents/Priti_484446.pdf"
    python pdf_splitter.py "C:/Documents/Priti_484446.pdf" "C:/Output"
"""

import sys
import os
import re
from pathlib import Path


def extract_number_from_filename(filename: str) -> str:
    
    name = Path(filename).stem          # e.g. "Priti_484446"
    match = re.search(r'\d+', name)     # find first number sequence
    return match.group() if match else name


def split_pdf(input_path: str, output_folder: str = None):
    """
    Split the PDF into photo + aadhaar + 10th + 12th files.

    Parameters
    ----------
    input_path   : full path to the source PDF
    output_folder: destination folder (default: 'output' next to the PDF)
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("[ERROR] 'pypdf' not installed. Run:  pip install pypdf")
        sys.exit(1)

    try:
        from pdf2image import convert_from_path
    except ImportError:
        print("[ERROR] 'pdf2image' not installed. Run:  pip install pdf2image")
        sys.exit(1)

    # ── Validate input ────────────────────────────────────────────────────────
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)
    if input_path.suffix.lower() != ".pdf":
        print(f"[ERROR] Not a PDF file: {input_path}")
        sys.exit(1)

    # ── Prepare output folder ─────────────────────────────────────────────────
    if output_folder:
        out_dir = Path(output_folder).resolve()
    else:
        out_dir = input_path.parent / "output"

    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Derive file prefix from filename ──────────────────────────────────────
    number = extract_number_from_filename(input_path.name)

    # ── Read PDF ──────────────────────────────────────────────────────────────
    reader = PdfReader(str(input_path))
    total_pages = len(reader.pages)
    print(f"\n📄 PDF loaded : {input_path.name}  ({total_pages} pages)")
    print(f"📁 Output dir : {out_dir}\n")

    # ── Page map: page_index → output filename ────────────────────────────────
    # Adjust this dict if the page order in your PDFs ever changes.
    page_map = {
        0: ("photo",   f"{number}.jpg",          "jpg"),
        1: ("aadhaar", f"{number}_aadhaar.pdf",  "pdf"),
        2: ("10th",    f"{number}_10th.pdf",      "pdf"),
        3: ("12th",    f"{number}_12th.pdf",      "pdf"),
    }

    results = []

    for page_idx, (label, filename, fmt) in page_map.items():
        if page_idx >= total_pages:
            print(f"  [SKIP] Page {page_idx+1} not found (PDF has only {total_pages} pages) → {label}")
            continue

        out_path = out_dir / filename

        if fmt == "jpg":
            # Render page to image
            images = convert_from_path(
                str(input_path),
                first_page=page_idx + 1,
                last_page=page_idx + 1,
                dpi=200,
            )
            images[0].save(str(out_path), "JPEG")
        else:
            writer = PdfWriter()
            writer.add_page(reader.pages[page_idx])
            with open(str(out_path), "wb") as f:
                writer.write(f)

        size_kb = out_path.stat().st_size // 1024
        print(f"  ✅  [{label:<8}]  →  {filename}  ({size_kb} KB)")
        results.append(out_path)

    print(f"\n🎉 Done! {len(results)} file(s) saved to: {out_dir}\n")


# ── CLI entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    pdf_path    = sys.argv[1]
    output_dir  = sys.argv[2] if len(sys.argv) >= 3 else None

    split_pdf(pdf_path, output_dir)
