"""
PDF Document Splitter — GUI Application
Splits every PDF in a folder into: Photo (JPG), Aadhaar, 10th, 12th files.
"""

import os
import queue
import re
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk


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


def split_pdf(input_path: str, output_folder: str, log_fn=print) -> int:
    """
    Split one PDF into photo + aadhaar + 10th + 12th outputs.
    Returns the number of files written.
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        log_fn("[ERROR] pypdf not installed — run: pip install pypdf")
        return 0

    try:
        from pdf2image import convert_from_path
    except ImportError:
        log_fn("[ERROR] pdf2image not installed — run: pip install pdf2image")
        return 0

    src = Path(input_path).resolve()
    if not src.exists() or src.suffix.lower() != ".pdf":
        log_fn(f"[SKIP]  Not a valid PDF: {src.name}")
        return 0

    out_dir = Path(output_folder).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    number = _extract_number(src.name)
    reader = PdfReader(str(src))
    total = len(reader.pages)

    log_fn(f"\n► {src.name}  ({total} page{'s' if total != 1 else ''})")

    page_map = {
        0: ("Photo",   f"{number}.jpg",          "jpg"),
        1: ("Aadhaar", f"{number}_aadhaar.pdf",  "pdf"),
        2: ("10th",    f"{number}_10th.pdf",     "pdf"),
        3: ("12th",    f"{number}_12th.pdf",     "pdf"),
    }

    count = 0
    for idx, (label, fname, fmt) in page_map.items():
        if idx >= total:
            log_fn(f"  [SKIP]  Page {idx + 1} missing → {label}")
            continue

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
        log_fn(f"  [OK]    {label:<8} →  {fname}  ({kb} KB)")
        count += 1

    return count


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
            self._finish(0, 0)
            return

        self._emit(f"Found {len(pdfs)} PDF file(s) — starting…\n", "hdr")

        total_pdfs = 0
        total_files = 0
        for pdf in pdfs:
            files = split_pdf(str(pdf), out_dir, log_fn=self._emit)
            if files > 0:
                total_pdfs += 1
                total_files += files

        self._finish(total_pdfs, total_files)

    def _finish(self, pdfs: int, files: int):
        self._emit(
            f"\n{'─' * 55}\nCompleted: {pdfs} PDF(s) processed, {files} output file(s) saved.",
            "hdr",
        )
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
    app = App()
    app.mainloop()
