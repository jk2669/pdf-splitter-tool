"""
PDF Document Splitter — GUI Application
Splits every PDF in a folder into: Photo (JPG), Aadhaar, 10th, 12th files.
"""

import os
import queue
import re
import shutil
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import license_manager


# ── Core splitting logic ───────────────────────────────────────────────────────

def _get_poppler_path() -> str | None:
    """Return bundled Poppler bin path when running as a PyInstaller exe."""
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "poppler")  # type: ignore[attr-defined]
    return None

def _extract_number(filename: str) -> str:
    name = Path(filename).stem
    match = re.search(r"\d+", name)
    return match.group() if match else name


REQUIRED_PAGES = 4
_PAGE_LABELS   = {0: "Photo", 1: "Aadhaar", 2: "10th", 3: "12th"}
_RESULT_PAGES  = (2, 3)   # 10th and 12th marksheet pages


def _ocr_page(pdf_path: str, page_num: int, poppler_path) -> str:
    """Render one page to an image and OCR it. Returns '' if unavailable."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
        if getattr(sys, "frozen", False):
            tess = os.path.join(sys._MEIPASS, "tesseract", "tesseract.exe")  # type: ignore[attr-defined]
            pytesseract.pytesseract.tesseract_cmd = tess
        images = convert_from_path(pdf_path, first_page=page_num,
                                   last_page=page_num, dpi=200,
                                   poppler_path=poppler_path)
        if images:
            return pytesseract.image_to_string(images[0], lang="eng")
    except Exception:
        pass
    return ""


def _failed_result_page(reader, src_path: str) -> str:
    """
    Scan 10th/12th pages for FAILED. Tries text layer first, falls back to OCR.
    Returns the page label (e.g. '10th') if found, empty string otherwise.
    """
    for idx in _RESULT_PAGES:
        if idx < len(reader.pages):
            text = reader.pages[idx].extract_text() or ""
            if not text.strip():                        # scanned — use OCR
                text = _ocr_page(src_path, idx + 1, _get_poppler_path())
            if "FAILED" in text.upper():
                return _PAGE_LABELS[idx]
    return ""


def _copy_to_failed(src: Path, out_dir: Path) -> None:
    failed_dir = out_dir / "failed"
    failed_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(src), str(failed_dir / src.name))


def split_pdf(input_path: str, output_folder: str, log_fn=print) -> tuple[int, str]:
    """
    Split one PDF into photo + aadhaar + 10th + 12th outputs.

    Returns (files_written, status) where status is:
      "ok"     — all 4 pages found and result is PASS
      "failed" — incomplete or FAILED result; original copied to output_folder/failed/
      "error"  — unreadable or not a PDF
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        log_fn("[ERROR] pypdf not installed — run: pip install pypdf")
        return 0, "error"

    try:
        from pdf2image import convert_from_path
    except ImportError:
        log_fn("[ERROR] pdf2image not installed — run: pip install pdf2image")
        return 0, "error"

    src = Path(input_path).resolve()
    if not src.exists() or src.suffix.lower() != ".pdf":
        log_fn(f"[SKIP]   Not a valid PDF: {src.name}")
        return 0, "error"

    out_dir = Path(output_folder).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(str(src))
        total  = len(reader.pages)
    except Exception as exc:
        log_fn(f"[ERROR]  Cannot read {src.name}: {exc}")
        return 0, "error"

    log_fn(f"\n► {src.name}  ({total} page{'s' if total != 1 else ''})")

    # ── Incomplete PDF → failed folder ────────────────────────────────────────
    if total < REQUIRED_PAGES:
        missing = [_PAGE_LABELS[i] for i in range(REQUIRED_PAGES) if i >= total]
        log_fn(f"  [FAILED] Missing page(s): {', '.join(missing)} — copying to failed/")
        _copy_to_failed(src, out_dir)
        return 0, "failed"

    # ── FAILED result on marksheet → failed folder ────────────────────────────
    failed_page = _failed_result_page(reader, str(src))
    if failed_page:
        log_fn(f"  [FAILED] Result is FAILED on {failed_page} marksheet — copying to failed/")
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
                str(src), first_page=idx + 1, last_page=idx + 1,
                dpi=200, poppler_path=_get_poppler_path(),
            )
            imgs[0].save(str(dest), "JPEG")
        else:
            writer = PdfWriter()
            writer.add_page(reader.pages[idx])
            with open(dest, "wb") as fh:
                writer.write(fh)

        kb = dest.stat().st_size // 1024
        log_fn(f"  [OK]     {label:<8} →  {fname}  ({kb} KB)")
        count += 1

    return count, "ok"


# ── GUI ────────────────────────────────────────────────────────────────────────

DARK_BG   = "#1e1e2e"
DARK_FG   = "#cdd6f4"
ACCENT    = "#89b4fa"
BTN_BG    = "#313244"
BTN_HOVER = "#45475a"
SUCCESS   = "#a6e3a1"
WARN      = "#f9e2af"
ERROR     = "#f38ba8"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PDF Document Splitter")
        self.geometry("720x560")
        self.resizable(False, False)
        self.configure(bg=DARK_BG)

        try:
            self.iconbitmap(default="")        # no custom icon required
        except Exception:
            pass

        self._q: queue.Queue = queue.Queue()
        self._running = False

        self._build_ui()
        self._poll()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        self._style()

        # ── Header ──
        hdr = tk.Frame(self, bg="#181825", pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="PDF Document Splitter",
                 font=("Segoe UI", 16, "bold"),
                 bg="#181825", fg=ACCENT).pack()
        tk.Label(hdr, text="Batch-split candidate PDFs into Photo · Aadhaar · 10th · 12th",
                 font=("Segoe UI", 9), bg="#181825", fg="#6c7086").pack()

        # ── Input folder row ──
        self._input_var = tk.StringVar()
        self._folder_row(" Input PDF Folder", self._input_var, self._browse_input)

        # ── Output folder row ──
        self._output_var = tk.StringVar()
        self._folder_row(" Output Folder", self._output_var, self._browse_output)

        # ── Execute button ──
        btn_frame = tk.Frame(self, bg=DARK_BG)
        btn_frame.pack(pady=(4, 8))

        self._exec_btn = tk.Button(
            btn_frame, text="  ▶  Execute  ",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT, fg="#1e1e2e", activebackground="#7aa2f7",
            relief="flat", bd=0, cursor="hand2",
            command=self._execute, padx=16, pady=6,
        )
        self._exec_btn.pack(side="left", padx=4)

        self._clear_btn = tk.Button(
            btn_frame, text="  Clear Log  ",
            font=("Segoe UI", 10),
            bg=BTN_BG, fg=DARK_FG, activebackground=BTN_HOVER,
            relief="flat", bd=0, cursor="hand2",
            command=self._clear_log, padx=12, pady=6,
        )
        self._clear_btn.pack(side="left", padx=4)

        # ── Progress bar ──
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=690)
        self._progress.pack(padx=14)

        # ── Log area ──
        log_frame = tk.Frame(self, bg="#11111b", bd=1, relief="flat")
        log_frame.pack(fill="both", expand=True, padx=14, pady=(8, 0))

        self._log = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            bg="#11111b", fg=DARK_FG,
            insertbackground=DARK_FG,
            selectbackground="#313244",
            relief="flat", bd=6,
            state="disabled",
            wrap="word",
        )
        self._log.pack(fill="both", expand=True)

        self._log.tag_config("ok",   foreground=SUCCESS)
        self._log.tag_config("warn", foreground=WARN)
        self._log.tag_config("err",  foreground=ERROR)
        self._log.tag_config("hdr",  foreground=ACCENT, font=("Consolas", 9, "bold"))

        # ── Status bar ──
        self._status_var = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self._status_var,
                 font=("Segoe UI", 8), bg="#181825", fg="#6c7086",
                 anchor="w", padx=10, pady=3).pack(fill="x", side="bottom")

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Horizontal.TProgressbar",
                    troughcolor="#313244", background=ACCENT,
                    bordercolor="#313244", lightcolor=ACCENT, darkcolor=ACCENT)

    def _folder_row(self, label: str, var: tk.StringVar, cmd):
        frame = tk.Frame(self, bg=DARK_BG)
        frame.pack(fill="x", padx=14, pady=(10, 0))

        tk.Label(frame, text=label, font=("Segoe UI", 9, "bold"),
                 bg=DARK_BG, fg="#6c7086", width=18, anchor="w").pack(side="left")

        entry = tk.Entry(frame, textvariable=var,
                         font=("Segoe UI", 9),
                         bg=BTN_BG, fg=DARK_FG,
                         insertbackground=DARK_FG,
                         relief="flat", bd=6)
        entry.pack(side="left", fill="x", expand=True)

        tk.Button(frame, text="Browse…",
                  font=("Segoe UI", 9),
                  bg=BTN_BG, fg=DARK_FG, activebackground=BTN_HOVER,
                  relief="flat", bd=0, cursor="hand2",
                  command=cmd, padx=10, pady=4).pack(side="left", padx=(6, 0))

    # ── Actions ───────────────────────────────────────────────────────────────

    def _browse_input(self):
        folder = filedialog.askdirectory(title="Select folder containing PDFs")
        if folder:
            self._input_var.set(folder)

    def _browse_output(self):
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self._output_var.set(folder)

    def _execute(self):
        in_dir = self._input_var.get().strip()
        out_dir = self._output_var.get().strip()

        if not in_dir:
            messagebox.showwarning("Missing Input", "Please select an input PDF folder.")
            return
        if not out_dir:
            messagebox.showwarning("Missing Output", "Please select an output folder.")
            return
        if not Path(in_dir).is_dir():
            messagebox.showerror("Invalid Folder", f"Input folder not found:\n{in_dir}")
            return

        self._exec_btn.config(state="disabled")
        self._progress.start(10)
        self._status_var.set("Processing…")
        self._running = True

        threading.Thread(
            target=self._run, args=(in_dir, out_dir), daemon=True
        ).start()

    def _run(self, in_dir: str, out_dir: str):
        pdfs = sorted(Path(in_dir).glob("*.pdf"))
        if not pdfs:
            self._emit("[WARN]  No PDF files found in the selected folder.", "warn")
            self._finish(0, 0, 0)
            return

        self._emit(f"Found {len(pdfs)} PDF file(s) — starting…\n", "hdr")

        n_ok = n_failed = n_files = 0
        for pdf in pdfs:
            files, status = split_pdf(str(pdf), out_dir, log_fn=self._emit)
            if status == "ok":
                n_ok    += 1
                n_files += files
            elif status == "failed":
                n_failed += 1

        self._finish(n_ok, n_files, n_failed)

    def _finish(self, n_ok: int, n_files: int, n_failed: int):
        lines = [f"\n{'─' * 55}"]
        lines.append(f"Split OK : {n_ok} PDF(s) → {n_files} output file(s)")
        if n_failed:
            lines.append(f"Failed   : {n_failed} PDF(s) copied to  output/failed/")
        lines.append(f"Total    : {n_ok + n_failed} PDF(s) processed")
        self._emit("\n".join(lines), "hdr")
        self._q.put(("__done__", None))

    # ── Log helpers ───────────────────────────────────────────────────────────

    def _emit(self, msg: str, tag: str = ""):
        self._q.put(("log", msg, tag))

    def _write_log(self, msg: str, tag: str):
        self._log.config(state="normal")
        self._log.insert(tk.END, msg + "\n", tag or None)
        self._log.see(tk.END)
        self._log.config(state="disabled")

    def _clear_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0", tk.END)
        self._log.config(state="disabled")

    def _poll(self):
        try:
            while True:
                item = self._q.get_nowait()
                if item[0] == "log":
                    _, msg, tag = item
                    # auto-tag lines that contain keywords
                    if not tag:
                        lo = msg.lower()
                        if "[ok]" in lo:
                            tag = "ok"
                        elif "[skip]" in lo or "[warn]" in lo:
                            tag = "warn"
                        elif "[error]" in lo:
                            tag = "err"
                    self._write_log(msg, tag)
                elif item[0] == "__done__":
                    self._progress.stop()
                    self._exec_btn.config(state="normal")
                    self._status_var.set("Ready")
                    self._running = False
        except queue.Empty:
            pass
        self.after(80, self._poll)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # License check — must pass before the window opens
    _ok, _msg = license_manager.verify()
    if not _ok:
        _root = tk.Tk()
        _root.withdraw()
        messagebox.showerror("License Error", _msg)
        _root.destroy()
        sys.exit(1)

    app = App()
    # Show license status in the title bar
    app.title(f"PDF Document Splitter  ·  {_msg}")
    app.mainloop()
