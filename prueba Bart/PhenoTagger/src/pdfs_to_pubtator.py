# src/pdfs_to_pubtator.py
import argparse, os, glob, re, pathlib
from pypdf import PdfReader

def extract_text(pdf_path: str) -> str:
    try:
        r = PdfReader(pdf_path)
        chunks = []
        for pg in r.pages:
            t = pg.extract_text() or ""
            chunks.append(t)
        return "\n".join(chunks)
    except Exception:
        return ""

def first_nonempty_line(text: str) -> str:
    for ln in text.splitlines():
        s = ln.strip()
        if s:
            return s
    return ""

def normalize(s: str) -> str:
    s = s.replace("\x00", "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def main(src: str, out: str):
    os.makedirs(out, exist_ok=True)
    pdfs = sorted(glob.glob(os.path.join(src, "*.pdf")))
    if not pdfs:
        print(f"No PDFs found in {src}")
        return
    saved, empty = 0, []
    for pdf in pdfs:
        text = extract_text(pdf)
        if not text or len(text.strip()) < 50:
            empty.append(pdf)
            continue
        pmid = pathlib.Path(pdf).stem
        title = first_nonempty_line(text)[:200] or pmid
        abstract = normalize(text)
        with open(os.path.join(out, f"{pmid}.PubTator"), "w", encoding="utf-8") as f:
            f.write(f"{pmid}|t|{normalize(title)}\n")
            f.write(f"{pmid}|a|{abstract}\n")
        saved += 1
    print(f"Saved {saved} PubTator files to {out}")
    if empty:
        print("Skipped (likely scanned or image-only PDFs):")
        for p in empty[:10]:
            print(" -", os.path.basename(p))
        if len(empty) > 10:
            print(f"  ...and {len(empty)-10} more")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="Carpeta con PDFs")
    ap.add_argument("--out", required=True, help="Carpeta de salida PubTator")
    args = ap.parse_args()
    main(args.src, args.out)
