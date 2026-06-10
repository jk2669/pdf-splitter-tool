@echo off
REM ============================================================
REM  Build PDF Document Splitter as a standalone Windows .exe
REM  Run this script on a Windows machine with Python installed
REM ============================================================

echo.
echo === PDF Document Splitter — EXE Builder ===
echo.

REM ── Step 1: Install/upgrade dependencies ────────────────────
echo [1/3] Installing dependencies...
pip install --upgrade pypdf pdf2image Pillow pyinstaller
if errorlevel 1 (
    echo [ERROR] pip install failed. Make sure Python is in PATH.
    pause
    exit /b 1
)

REM ── Step 2: Build the exe ────────────────────────────────────
echo.
echo [2/3] Building executable...

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "PDFSplitter" ^
    --hidden-import pypdf ^
    --hidden-import pdf2image ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.JpegImagePlugin ^
    pdf_splitter_gui.py

if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

REM ── Step 3: Copy output ──────────────────────────────────────
echo.
echo [3/3] Done!
echo.
echo  Executable location:
echo    dist\PDFSplitter.exe
echo.
echo  IMPORTANT — Poppler requirement:
echo  pdf2image needs Poppler binaries to convert PDF pages to images.
echo  Download from:  https://github.com/oschwartz10612/poppler-windows/releases
echo  Extract and add the bin\ folder to your system PATH,
echo  OR copy the bin\ contents next to PDFSplitter.exe.
echo.
pause
