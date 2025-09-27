#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, re, json, glob, random, argparse, unicodedata
from pathlib import Path

LIGS = {"\ufb00":"ff","\ufb01":"fi","\ufb02":"fl","\ufb03":"ffi","\ufb04":"ffl","\ufb05":"st","\ufb06":"st"}

def uclean(s:str)->str:
    if not s: return ""
    s = unicodedata.normalize("NFKC", s)
    for k,v in LIGS.items(): s = s.replace(k,v)
    s = s.replace("\u00AD","").replace("\u200B","").replace("\u200D","")
    s = s.replace("\u00A0"," ").replace("“","\"").replace("”","\"").replace("’","'")
    s = s.replace("–","-").replace("—","-")
    s = re.sub(r"[ \t]+"," ", s)
    return s.strip()

def load_terms(dict_dir: Path):
    exp = dict_dir/"expanded_terms.json"
    dic = dict_dir/"noabb_lemma.dic"
    obo = dict_dir/"obo.json"
    if exp.exists():
        t = json.loads(exp.read_text(encoding="utf-8"))
        return [x for x in t if isinstance(x,str)]
    if dic.exists():
        return [l.strip() for l in dic.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip()]
    if obo.exists():
        data = json.loads(obo.read_text(encoding="utf-8"))
        vals = data.values() if isinstance(data,dict) else data
        out=[]
        for node in vals:
            if not isinstance(node,dict): continue
            names = node.get("name", [])
            if isinstance(names,str): names=[names]
            out += [n for n in (names or []) if n]
            syns = node.get("synonym", [])
            for syn in syns or []:
                t = syn[0] if isinstance(syn,(list,tuple)) and syn else syn
                if isinstance(t,str) and t: out.append(t)
        return out
    raise FileNotFoundError(f"No encontré diccionario en {dict_dir}")

def compile_patts(terms, stopset, mode):
    patts=[]
    use = []
    for t in set(uclean(x) for x in terms):
        if not t: continue
        if t.lower() in stopset:  # términos demasiado genéricos
            continue
        if mode == "multiword" and (" " not in t and "-" not in t):
            continue
        patt = r"(?i)(?<!\w)"+re.escape(t).replace("\\-","[- ]")+r"(?!\w)"
        patts.append(re.compile(patt))
        use.append(t)
    return patts, set(use)

def sentence_split(text):
    # split por fin de oración o saltos dobles
    parts = re.split(r"(?<=[\.!?])\s+|\n{2,}", text)
    return [p.strip() for p in parts if p.strip()]

def has_any(pats, s):
    return any(p.search(s) for p in pats)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-i","--in_dir", default="/textoss")
    ap.add_argument("-d","--dict_dir", default="diccionarios")
    ap.add_argument("-o","--out", default="data/negatives.txt")
    ap.add_argument("--max", type=int, default=8000)
    ap.add_argument("--min_chars", type=int, default=40)
    ap.add_argument("--max_chars", type=int, default=1200)
    ap.add_argument("--filter_mode", choices=["all","multiword"], default="multiword",
                    help="Criterio para filtrar oraciones con términos del diccionario")
    ap.add_argument("--stoplist_file", type=str, default=None,
                    help="Archivo con términos genéricos (uno por línea) a ignorar en el filtrado")
    ap.add_argument("--max_per_doc", type=int, default=400,
                    help="Tope de oraciones seleccionadas por archivo (balance)")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--fallback_if_zero", action="store_true",
                    help="Si no hay candidatos tras el filtrado, guardar por longitud (sin filtrar)")
    args = ap.parse_args()

    random.seed(args.seed)
    terms = load_terms(Path(args.dict_dir))

    # stoplist por defecto + archivo opcional
    default_stop = {
        "data","dataset","analysis","analyses","method","methods","study","studies",
        "question","questions","interview","interviews","participants","participant",
        "result","results","figure","table","paper","appendix","section","introduction",
        "discussion","conclusion","research","model","models","approach","technique","techniques"
    }
    if args.stoplist_file and os.path.exists(args.stoplist_file):
        extra = {l.strip().lower() for l in open(args.stoplist_file,encoding="utf-8") if l.strip()}
        default_stop |= extra

    pats, used_terms = compile_patts(terms, default_stop, args.filter_mode)
    if not pats:
        print("[WARN] No quedaron términos para filtrar negativos (stoplist+modo). Se usará solo longitud.")

    files = sorted(glob.glob(os.path.join(args.in_dir,"*.txt")))
    pool=[]
    per_doc_counts = {}

    for p in files:
        txt = uclean(open(p,"r",encoding="utf-8",errors="ignore").read())
        sents = sentence_split(txt)
        doc_sel = []
        for s in sents:
            if not (args.min_chars <= len(s) <= args.max_chars): 
                continue
            if pats and has_any(pats, s):
                continue
            doc_sel.append(s)
            if args.max_per_doc and len(doc_sel) >= args.max_per_doc:
                break
        pool.extend(doc_sel)
        per_doc_counts[os.path.basename(p)] = len(doc_sel)

    random.shuffle(pool)
    sel = pool[:args.max]

    if len(sel)==0 and args.fallback_if_zero:
        # Plan B: usa solo longitud, sin filtrar por diccionario
        print("[WARN] 0 negativas con el filtrado. Activando fallback por longitud (sin filtro).")
        for p in files:
            txt = uclean(open(p,"r",encoding="utf-8",errors="ignore").read())
            sents = [s for s in sentence_split(txt) if args.min_chars <= len(s) <= args.max_chars]
            random.shuffle(sents)
            take = sents[:args.max_per_doc] if args.max_per_doc else sents
            pool.extend(take)
        random.shuffle(pool)
        sel = pool[:args.max]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out,"w",encoding="utf-8") as w:
        for s in sel: w.write(s.replace("\n"," ")+"\n")

    print(f"OK -> {args.out} ({len(sel)} oraciones negativas)")
    # resumen útil
    total_before = sum(per_doc_counts.values())
    print(f"[DBG] candidatos por doc (post-filtro): {total_before}   archivos: {len(files)}")
    print(f"[DBG] términos usados para filtrar ({len(used_terms)}): {sorted(list(used_terms))[:15]}{' ...' if len(used_terms)>15 else ''}")

if __name__ == "__main__":
    main()
