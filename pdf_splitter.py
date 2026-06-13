"""
PDF Document Splitter
=====================
Splits candidate PDFs into separate files:
  - <number>.jpg           → Photo (page 1)
  - <number>_aadhaar.pdf  → Aadhaar card (page 2)
  - <number>_10th.pdf     → 10th marksheet (page 3)
  - <number>_12th.pdf     → 12th marksheet (page 4)

PDFs with fewer than 4 pages are not split — they are copied to
output_folder/failed/ for manual review.

Usage:
    # Single PDF
    python pdf_splitter.py <path_to_pdf> [output_folder]

    # Entire folder (batch)
    python pdf_splitter.py <folder_of_pdfs> [output_folder]

Examples:
    python pdf_splitter.py "Downloads/Priti_484446.pdf"
    python pdf_splitter.py "Downloads/Priti_484446.pdf" "C:/Output"
    python pdf_splitter.py "Downloads/pdfs/"
    python pdf_splitter.py "Downloads/pdfs/" "C:/Output"
"""

import re
import shutil
import sys
from pathlib import Path

REQUIRED_PAGES = 4
_PAGE_LABELS   = {0: "Photo", 1: "Aadhaar", 2: "10th", 3: "12th"}
_RESULT_PAGES  = (2, 3)   # 10th and 12th marksheet pages


def _extract_number(filename: str) -> str:
    name  = Path(filename).stem
    match = re.search(r"\d+", name)
    return match.group() if match else name


def _failed_result_page(reader) -> str:
    """
    Scan the 10th and 12th pages for the word FAILED in the result column.
    Returns the page label (e.g. "10th") if found, empty string otherwise.
    """
    for idx in _RESULT_PAGES:
        if idx < len(reader.pages):
            text = reader.pages[idx].extract_text() or ""
            if "FAILED" in text.upper():
                return _PAGE_LABELS[idx]
    return ""


def _copy_to_failed(src: Path, out_dir: Path) -> None:
    failed_dir = out_dir / "failed"
    failed_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(failed_dir / src.name))


def split_one(input_path: str, output_folder: str) -> tuple[int, str]:
    """
    Split a single PDF.  Returns (files_written, status).
    status is "ok", "failed" (< 4 pages), or "error".
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("[ERROR] 'pypdf' not installed.  Run:  pip install pypdf")
        sys.exit(1)

    try:
        from pdf2image import convert_from_path
    except ImportError:
        print("[ERROR] 'pdf2image' not installed.  Run:  pip install pdf2image")
        sys.exit(1)

    src = Path(input_path).resolve()
    if not src.exists() or src.suffix.lower() != ".pdf":
        print(f"  [SKIP]   Not a valid PDF: {src.name}")
        return 0, "error"

    out_dir = Path(output_folder).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(str(src))
        total  = len(reader.pages)
    except Exception as exc:
        print(f"  [ERROR]  Cannot read {src.name}: {exc}")
        return 0, "error"

    print(f"\n► {src.name}  ({total} page{'s' if total != 1 else ''})")

    # ── Incomplete → failed folder ────────────────────────────────────────────
    if total < REQUIRED_PAGES:
        missing = [_PAGE_LABELS[i] for i in range(REQUIRED_PAGES) if i >= total]
        print(f"  [FAILED] Missing page(s): {', '.join(missing)} — copying to failed/")
        _copy_to_failed(src, out_dir)
        return 0, "failed"

    # ── FAILED result on marksheet → failed folder ────────────────────────────
    failed_page = _failed_result_page(reader)
    if failed_page:
        print(f"  [FAILED] Result is FAILED on {failed_page} marksheet — copying to failed/")
        _copy_to_failed(src, out_dir)
        return 0, "failed"

    # ── Full PDF → split ──────────────────────────────────────────────────────
    number   = _extract_number(src.name)
    page_map = {
        0: ("Photo",   f"{number}.jpg",         "jpg"),
        1: ("Aadhaar", f"{number}_aadhaar.pdf", "pdf"),
        2: ("10th",    f"{number}_10th.pdf",    "pdf"),
        3: ("12th",    f"{number}_12th.pdf",    "pdf"),
    }

    count = 0
    for idx, (label, fname, fmt) in page_map.items():
        dest = out_dir / fname
        if fmt == "jpg":
            imgs = convert_from_path(
                str(src), first_page=idx + 1, last_page=idx + 1, dpi=200
            )
            imgs[0].save(str(dest), "JPEG")
        else:
            writer = PdfWriter()
            writer.add_page(reader.pages[idx])
            with open(dest, "wb") as fh:
                writer.write(fh)

        kb = dest.stat().st_size // 1024
        print(f"  [OK]     {label:<8} →  {fname}  ({kb} KB)")
        count += 1

    return count, "ok"


def split_folder(input_folder: str, output_folder: str) -> None:
    """Batch-process every PDF inside input_folder."""
    src_dir = Path(input_folder).resolve()
    pdfs    = sorted(src_dir.glob("*.pdf"))

    if not pdfs:
        print(f"[WARN] No PDF files found in: {src_dir}")
        return

    print(f"\nFound {len(pdfs)} PDF file(s) in: {src_dir}")
    print(f"Output folder : {output_folder}\n")

    n_ok = n_failed = n_files = 0
    for pdf in pdfs:
        files, status = split_one(str(pdf), output_folder)
        if status == "ok":
            n_ok    += 1
            n_files += files
        elif status == "failed":
            n_failed += 1

    print(f"\n{'─' * 50}")
    print(f"Split OK : {n_ok} PDF(s) → {n_files} output file(s)")
    if n_failed:
        print(f"Failed   : {n_failed} PDF(s) → copied to output/failed/")
    print(f"Total    : {n_ok + n_failed} PDF(s) processed\n")


# ── CLI entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    target     = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) >= 3 else None
    src        = Path(target).resolve()

    if src.is_dir():
        out = output_dir or str(src / "output")
        split_folder(str(src), out)
    elif src.is_file():
        out = output_dir or str(src.parent / "output")
        split_one(str(src), out)
    else:
        print(f"[ERROR] Path not found: {src}")
        sys.exit(1)
