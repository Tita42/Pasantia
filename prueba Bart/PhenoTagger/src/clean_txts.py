import re, os, glob, io

RAW = "data/raw_txt"
OUT = "data/clean_txt"
os.makedirs(OUT, exist_ok=True)

def collapse_spaced_letters(s):
    # Une secuencias tipo "M E T H O D S" -> "METHODS"
    return re.sub(r'(?:(?<=\s)|^)(?:[A-Za-z]\s){2,}[A-Za-z](?=\s|$)',
                  lambda m: m.group(0).replace(' ', ''), s)

def clean_text(t):
    t = t.replace('\r', '')
    t = re.sub(r'-\n', '', t)         # une palabras cortadas con guión al fin de línea
    t = t.replace('\n', ' ')          # todo en una línea (simple)
    t = collapse_spaced_letters(t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

for path in glob.glob(os.path.join(RAW, "*.txt")):
    with io.open(path, 'r', encoding='utf-8', errors='ignore') as f:
        txt = f.read()
    cleaned = clean_text(txt)
    out = os.path.join(OUT, os.path.basename(path))
    with io.open(out, 'w', encoding='utf-8') as g:
        g.write(cleaned)
    print("✓", os.path.basename(path), "->", out, "| chars:", len(cleaned))
