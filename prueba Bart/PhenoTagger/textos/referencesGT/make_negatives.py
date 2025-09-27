# Extrae texto de todos los PDFs de una carpeta elegida en Finder
# y guarda un único negatives.txt (para PhenoTagger: Build_distant_corpus.py -f ...)

import os, sys
from pathlib import Path
from pdfminer.high_level import extract_text

# diálogos nativos (Finder)
try:
    import tkinter as tk
    from tkinter import filedialog
except Exception as e:
    print("Tkinter no disponible:", e)
    sys.exit(1)

root = tk.Tk()
root.withdraw()

in_dir = filedialog.askdirectory(title="Elegí la carpeta con PDFs")
if not in_dir:
    print("No elegiste carpeta. Saliendo.")
    sys.exit(0)

out_path = filedialog.asksaveasfilename(
    title="Elegí dónde guardar negatives.txt",
    defaultextension=".txt",
    initialfile="negatives.txt",
    filetypes=[("Text", "*.txt")]
)
if not out_path:
    print("No elegiste archivo de salida. Saliendo.")
    sys.exit(0)

in_dir = Path(in_dir)
pdfs = [p for p in in_dir.rglob("*.pdf")]

print(f"Encontrados {len(pdfs)} PDFs. Extrayendo texto…")
total_chars = 0
with open(out_path, "w", encoding="utf-8") as fout:
    for i, pdf in enumerate(pdfs, 1):
        try:
            text = extract_text(str(pdf)) or ""
            text = text.replace("\x0c", "\n").strip()
            if text:
                fout.write(text + "\n\n")
                total_chars += len(text)
            print(f"[{i}/{len(pdfs)}] {pdf.name}: {len(text)} chars")
        except Exception as e:
            print(f"   ⚠️  Error con {pdf.name}: {e}")

print(f"\nListo. Escribí {total_chars} caracteres en:\n{out_path}")
print("Nota: si algún PDF es un escaneo (solo imágenes), saldrá vacío; para esos usamos OCR luego.")
