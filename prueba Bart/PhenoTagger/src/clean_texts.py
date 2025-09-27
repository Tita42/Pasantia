# src/clean_texts.py
import re, os, argparse, pathlib

def normalize(txt: str) -> str:
    # des–ligaduras
    txt = txt.replace("ﬁ","fi").replace("ﬂ","fl")
    # unir palabras cortadas por salto de línea (e.g., docu-\nment)
    txt = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', txt)
    # colapsar MAYÚSCULAS espaciadas: "M E T H O D S" -> "METHODS"
    txt = re.sub(r'(?:(?<=\b)|^)([A-Z])(?:\s[A-Z]){2,}(?=\b|$)',
                 lambda m: m.group(0).replace(" ",""), txt)
    # convertir saltos de línea a espacios
    txt = re.sub(r'\s*\n+\s*', ' ', txt)
    # espacios múltiples -> 1
    txt = re.sub(r'[ \t]{2,}', ' ', txt)
    return txt.strip()

ap = argparse.ArgumentParser()
ap.add_argument('--src', required=True)
ap.add_argument('--dst', required=True)
args = ap.parse_args()

os.makedirs(args.dst, exist_ok=True)
for p in sorted(pathlib.Path(args.src).glob('*.txt')):
    t = p.read_text(encoding='utf-8', errors='ignore')
    (pathlib.Path(args.dst)/p.name).write_text(normalize(t), encoding='utf-8')
print("OK:", args.dst)
