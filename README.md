# PDF Document Splitter

Automatically splits a candidate PDF (photo + Aadhaar + marksheets) into
separate named files.

---

## Output file naming

| Page | Content      | Output file             |
|------|-------------|-------------------------|
| 1    | Photo        | `<number>.jpg`          |
| 2    | Aadhaar card | `<number>_aadhaar.pdf`  |
| 3    | 10th marks   | `<number>_10th.pdf`     |
| 4    | 12th marks   | `<number>_12th.pdf`     |

The `<number>` is extracted automatically from the PDF filename.  
Example: `Priti_484446.pdf` → prefix is `484446`

---

## Setup (one time)

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Poppler (required by pdf2image)

**Windows:**
1. Download from https://github.com/oschwartz10612/poppler-windows/releases
2. Extract and add the `bin/` folder to your system PATH
   - Search "Environment Variables" in Start menu
   - Edit `Path` → Add the poppler `bin` folder path

**macOS:**
```bash
brew install poppler
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install poppler-utils
```

---

## Usage

### Basic (output saved to `output/` folder next to the PDF)
```bash
python pdf_splitter.py "C:\Documents\Priti_484446.pdf"
```

### Custom output folder
```bash
python pdf_splitter.py "C:\Documents\Priti_484446.pdf" "C:\Output\Priti"
```

---

## Running in VS Code

1. Open the `pdf_splitter` folder in VS Code
2. Open the **Terminal** (`Ctrl + \``)
3. Run:
   ```bash
   python pdf_splitter.py "full\path\to\your\file.pdf"
   ```

---

## Example output

```
📄 PDF loaded : Priti_484446.pdf  (4 pages)
📁 Output dir : C:\Documents\output

  ✅  [photo   ]  →  484446.jpg          (210 KB)
  ✅  [aadhaar ]  →  484446_aadhaar.pdf  (185 KB)
  ✅  [10th    ]  →  484446_10th.pdf     (172 KB)
  ✅  [12th    ]  →  484446_12th.pdf     (168 KB)

🎉 Done! 4 file(s) saved to: C:\Documents\output
```
