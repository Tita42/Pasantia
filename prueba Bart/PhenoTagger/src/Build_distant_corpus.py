#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build_distant_corpus.py
-----------------------
Genera un dataset de distant supervision en formato CoNLL a partir de:
- Un directorio de TXT (p.ej. /textoss) donde se buscan menciones por diccionario.
- (Opcional) Un negatives.txt del que se toman oraciones que NO contengan términos.

Soporta diccionarios en:
- diccionarios/expanded_terms.json      (lista de strings)
- diccionarios/noabb_lemma.dic          (1 término por línea)
- diccionarios/obo.json                 (estructura flexible: name, synonym)

Cambia guiones/espacios, plurales simples (opcional) y normaliza Unicode.
"""

import argparse
import json
import os
import random
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable, List, Tuple, Dict, Set, Optional

# ---------------------------
# Normalización y utilidades
# ---------------------------

LIGATURES = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl",
    "\ufb03": "ffi", "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st"
}

WORD_RE = re.compile(
    r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+(?:[-/][A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]+)*|[^\s]",
    re.UNICODE
)

def uclean(s: str) -> str:
    """Limpieza básica: NFKC, ligaduras, NBSP→espacio, comillas/guiones."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    for k, v in LIGATURES.items():
        s = s.replace(k, v)
    s = s.replace("\u00AD", "")   # soft hyphen
    s = s.replace("\u200B", "")   # zero-width space
    s = s.replace("\u200D", "")   # zero-width joiner
    s = s.replace("\u00A0", " ")
    s = s.replace("“", "\"").replace("”", "\"").replace("’", "'")
    s = s.replace("–", "-").replace("—", "-")
    # colapsar espacios
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()

def norm_lower(s: str) -> str:
    return uclean(s).lower()

def hyphen_space_variants(term: str) -> Set[str]:
    """Genera variantes guion↔espacio."""
    t = uclean(term)
    out = {t}
    if "-" in t:
        out.add(t.replace("-", " "))
    if " " in t:
        out.add(t.replace(" ", "-"))
    return out

def plural_variants(term: str) -> Set[str]:
    """Plurales simples (ES/EN naïve)."""
    t = uclean(term)
    out = {t}
    if re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]$", t):
        out.add(t + "s")
        out.add(t + "es")
    return out

def compile_term_patterns(terms: Iterable[str]) -> List[Tuple[str, re.Pattern]]:
    """
    Compila regex por término con tolerancia guion/espacio:
    'document-analysis' matchea 'document-analysis' y 'document analysis'.
    Usa límites de palabra (?<!\w)/(?!\w).
    """
    patterns = []
    for t in sorted(set(uclean(x) for x in terms), key=lambda x: (-len(x), x)):
        if not t:
            continue
        patt = r"(?i)(?<!\w)" + re.escape(t).replace(r"\-", r"[- ]") + r"(?!\w)"
        patterns.append((t, re.compile(patt)))
    return patterns

def tokenize_with_offsets(text: str) -> List[Tuple[str, int, int]]:
    """Tokeniza preservando offsets (sobre texto ya 'uclean')."""
    toks = []
    for m in WORD_RE.finditer(text):
        toks.append((m.group(0), m.start(), m.end()))
    return toks

# --------------------------------
# Carga robusta del diccionario
# --------------------------------

def load_terms_from_obo_json(path: Path) -> List[str]:
    """
    Admite varias estructuras:
    {
      "ID": {"name": ["X","Y"] or "X", "synonym": [["S",...], "S2", ...], ...},
      ...
    }
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] No pude leer {path}: {e}", file=sys.stderr)
        return []

    out = []
    if isinstance(data, dict):
        values = data.values()
    elif isinstance(data, list):
        values = data
    else:
        print("[WARN] obo.json en formato no reconocido; ignorando.", file=sys.stderr)
        return []

    for node in values:
        if not isinstance(node, dict):
            continue
        names = node.get("name", [])
        if isinstance(names, str):
            names = [names]
        for n in names or []:
            if n:
                out.append(n)

        syns = node.get("synonym", [])
        # Puede venir como lista de strings o lista de listas/tuplas
        for syn in syns or []:
            if isinstance(syn, (list, tuple)) and syn:
                t = syn[0]
            else:
                t = syn
            if isinstance(t, str) and t:
                out.append(t)
    return out

def load_dictionary_terms(dict_dir: Path) -> List[str]:
    """
    Intenta, en orden:
      1) expanded_terms.json (lista de strings)
      2) noabb_lemma.dic (línea por término)
      3) obo.json (con guards)
    """
    exp = dict_dir / "expanded_terms.json"
    dic = dict_dir / "noabb_lemma.dic"
    obo = dict_dir / "obo.json"

    if exp.exists():
        try:
            terms = json.loads(exp.read_text(encoding="utf-8"))
            if not isinstance(terms, list):
                raise ValueError("expanded_terms.json no es una lista")
            return [t for t in terms if isinstance(t, str)]
        except Exception as e:
            print(f"[WARN] No pude leer expanded_terms.json: {e}", file=sys.stderr)

    if dic.exists():
        try:
            return [uclean(x) for x in dic.read_text(encoding="utf-8").splitlines() if x.strip()]
        except Exception as e:
            print(f"[WARN] No pude leer noabb_lemma.dic: {e}", file=sys.stderr)

    if obo.exists():
        terms = load_terms_from_obo_json(obo)
        if terms:
            return terms

    raise FileNotFoundError(
        f"No encontré diccionario en {dict_dir} (esperaba expanded_terms.json o noabb_lemma.dic o obo.json)"
    )

# --------------------------------
# Etiquetado por diccionario
# --------------------------------

def find_matches(text_clean: str, patterns: List[Tuple[str, re.Pattern]]) -> List[Tuple[int, int, str]]:
    """
    Devuelve lista de spans (start, end, term) sobre text_clean.
    Resuelve solapamientos quedándose con los matches más largos primero.
    """
    all_hits = []
    for canon, patt in patterns:
        for m in patt.finditer(text_clean):
            all_hits.append((m.start(), m.end(), canon))

    # Resolver solapamiento: greedy por mayor longitud
    all_hits.sort(key=lambda x: (-(x[1]-x[0]), x[0]))
    chosen = []
    used = [False] * len(all_hits)

    spans_taken = []

    for i, (s, e, t) in enumerate(all_hits):
        overlap = False
        for (ts, te) in spans_taken:
            if not (e <= ts or s >= te):
                overlap = True
                break
        if not overlap:
            chosen.append((s, e, t))
            spans_taken.append((s, e))

    # Orden por inicio
    chosen.sort(key=lambda x: x[0])
    return chosen

def label_tokens_conll(text_clean: str,
                       toks: List[Tuple[str, int, int]],
                       spans: List[Tuple[int, int, str]],
                       label_prefix: str = "ONTO") -> List[Tuple[str, str]]:
    """
    Asigna BIO a tokens dado spans de menciones en coordenadas de text_clean.
    """
    labels = ["O"] * len(toks)

    for (s, e, _term) in spans:
        # marcar tokens que caigan dentro del span
        covered = [i for i, (_tok, ts, te) in enumerate(toks) if not (te <= s or ts >= e)]
        if not covered:
            continue
        labels[covered[0]] = f"B-{label_prefix}"
        for i in covered[1:]:
            labels[i] = f"I-{label_prefix}"

    return [(toks[i][0], labels[i]) for i in range(len(toks))]

def split_sentences_from_tokens(tok_offsets: List[Tuple[str, int, int]]) -> List[List[Tuple[str, int, int]]]:
    """
    Segmentación sencilla en oraciones usando signos y saltos de línea dobles como indicadores.
    """
    sents = []
    cur = []
    last_end = 0
    for tok, s, e in tok_offsets:
        cur.append((tok, s, e))
        # fin de oración por puntuación fuerte
        if tok in {".", "!", "?"} or "\n\n" in tok:
            sents.append(cur)
            cur = []
        last_end = e
    if cur:
        sents.append(cur)
    return sents

# --------------------------------
# Negativos controlados
# --------------------------------

def sentence_split_simple(text_clean: str) -> List[str]:
    # split por signos de fin y saltos dobles; conserva contenido
    parts = re.split(r"(?<=[\.!?])\s+|\n{2,}", text_clean)
    return [p.strip() for p in parts if p.strip()]

def filter_negative_sentences(candidates: List[str], patterns: List[Tuple[str, re.Pattern]]) -> List[str]:
    out = []
    for sent in candidates:
        bad = False
        for _canon, patt in patterns:
            if patt.search(sent):
                bad = True
                break
        if not bad:
            out.append(sent)
    return out

# --------------------------------
# Pipeline principal
# --------------------------------

def build_conll_from_dir(in_dir: Path,
                         dict_terms: List[str],
                         out_conll: Path,
                         expand_hyphen_space: bool = True,
                         expand_plurals: bool = True,
                         label_prefix: str = "ONTO",
                         max_sentences: Optional[int] = None,
                         seed: int = 13) -> Dict[str, int]:
    random.seed(seed)

    # expandir términos
    tset: Set[str] = set()
    for t in dict_terms:
        v = {uclean(t)}
        if expand_hyphen_space:
            v |= hyphen_space_variants(t)
        if expand_plurals:
            tmp = set()
            for vi in v:
                tmp |= plural_variants(vi)
            v |= tmp
        tset |= v

    patterns = compile_term_patterns(tset)

    files = sorted([p for p in in_dir.glob("*.txt") if p.is_file()])
    out_conll.parent.mkdir(parents=True, exist_ok=True)

    stats = defaultdict(int)
    written = 0

    with out_conll.open("w", encoding="utf-8", newline="\n") as fout:
        for fp in files:
            raw = fp.read_text(encoding="utf-8", errors="ignore")
            text = uclean(raw)
            toks = tokenize_with_offsets(text)
            spans = find_matches(text, patterns)
            sents = split_sentences_from_tokens(toks)

            for sent in sents:
                sent_text = text[sent[0][1]: sent[-1][2]]
                # etiquetar solo esta oración
                # recalcular spans que intersectan la oración
                local_spans = []
                for (s, e, term) in spans:
                    if not (e <= sent[0][1] or s >= sent[-1][2]):
                        # recorta a los límites de la oración para robustez
                        ss = max(s, sent[0][1])
                        ee = min(e, sent[-1][2])
                        if ss < ee:
                            local_spans.append((ss, ee, term))

                conll = label_tokens_conll(text, sent, local_spans, label_prefix=label_prefix)
                for tok, lab in conll:
                    fout.write(f"{tok}\t{lab}\n")
                fout.write("\n")
                written += 1
                stats["sentences"] += 1
                stats["mentions"] += len(local_spans)

                if max_sentences and written >= max_sentences:
                    break
            if max_sentences and written >= max_sentences:
                break

    stats["files"] = len(files)
    return stats

def append_negatives_from_file(neg_file: Path,
                               dict_terms: List[str],
                               out_conll: Path,
                               max_neg_sentences: int = 10000,
                               expand_hyphen_space: bool = True,
                               expand_plurals: bool = True,
                               seed: int = 13) -> int:
    random.seed(seed)

    tset: Set[str] = set()
    for t in dict_terms:
        v = {uclean(t)}
        if expand_hyphen_space:
            v |= hyphen_space_variants(t)
        if expand_plurals:
            tmp = set()
            for vi in v:
                tmp |= plural_variants(vi)
            v |= tmp
        tset |= v
    patterns = compile_term_patterns(tset)

    raw = neg_file.read_text(encoding="utf-8", errors="ignore")
    text = uclean(raw)
    sents = sentence_split_simple(text)
    sents = filter_negative_sentences(sents, patterns)

    random.shuffle(sents)
    sents = sents[:max_neg_sentences]

    written = 0
    with out_conll.open("a", encoding="utf-8", newline="\n") as fout:
        for sent in sents:
            toks = tokenize_with_offsets(sent)
            for tok, _, _ in toks:
                fout.write(f"{tok}\tO\n")
            fout.write("\n")
            written += 1
    return written

# --------------------------------
# CLI
# --------------------------------

def parse_args():
    ap = argparse.ArgumentParser(description="Construye distant supervision en CoNLL usando un diccionario.")
    ap.add_argument("-i", "--in_dir", type=str, default="/textoss",
                    help="Directorio con TXT para buscar menciones (default: /textoss)")
    ap.add_argument("-d", "--dict_dir", type=str, default="diccionarios",
                    help="Directorio con el diccionario (expanded_terms.json / noabb_lemma.dic / obo.json)")
    ap.add_argument("-f", "--negatives", type=str, default=None,
                    help="Archivo negatives.txt (opcional) para agregar oraciones O puras filtradas")
    ap.add_argument("-o", "--out_dir", type=str, default="data/distant_train_data",
                    help="Directorio de salida (default: data/distant_train_data)")
    ap.add_argument("-O", "--outfile", type=str, default="distant_train.conll",
                    help="Nombre del archivo CoNLL (default: distant_train.conll)")
    ap.add_argument("--max_sentences", type=int, default=None,
                    help="Máximo de oraciones POS/mixtas tomadas del in_dir")
    ap.add_argument("--max_neg_sentences", type=int, default=10000,
                    help="Máximo de oraciones negativas a agregar desde negatives.txt")
    ap.add_argument("--no_expand_hyphen_space", action="store_true",
                    help="No generar variantes guion↔espacio")
    ap.add_argument("--no_expand_plurals", action="store_true",
                    help="No generar variantes de plurales simples")
    ap.add_argument("--label_prefix", type=str, default="ONTO",
                    help="Prefijo de etiqueta BIO (default: ONTO)")
    ap.add_argument("--seed", type=int, default=13, help="Seed aleatoria")
    return ap.parse_args()

def main():
    args = parse_args()

    in_dir = Path(args.in_dir)
    dict_dir = Path(args.dict_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / args.outfile

    print(f"[INFO] Cargando términos desde {dict_dir} ...")
    terms = load_dictionary_terms(dict_dir)
    print(f"[INFO] Términos base: {len(terms)}")

    print(f"[INFO] Generando CoNLL desde {in_dir} -> {out_file}")
    stats = build_conll_from_dir(
        in_dir=in_dir,
        dict_terms=terms,
        out_conll=out_file,
        expand_hyphen_space=not args.no_expand_hyphen_space,
        expand_plurals=not args.no_expand_plurals,
        label_prefix=args.label_prefix,
        max_sentences=args.max_sentences,
        seed=args.seed
    )
    print(f"[OK] Oraciones escritas: {stats['sentences']}, menciones detectadas: {stats['mentions']}, archivos: {stats['files']}")

    if args.negatives:
        neg_path = Path(args.negatives)
        if neg_path.exists():
            print(f"[INFO] Agregando negativos desde {neg_path} (filtrados por diccionario)...")
            n_added = append_negatives_from_file(
                neg_file=neg_path,
                dict_terms=terms,
                out_conll=out_file,
                max_neg_sentences=args.max_neg_sentences,
                expand_hyphen_space=not args.no_expand_hyphen_space,
                expand_plurals=not args.no_expand_plurals,
                seed=args.seed
            )
            print(f"[OK] Oraciones negativas agregadas: {n_added}")
        else:
            print(f"[WARN] No existe negatives.txt en {neg_path}, se omite.", file=sys.stderr)

    print(f"[DONE] Archivo final: {out_file}")

if __name__ == "__main__":
    main()
