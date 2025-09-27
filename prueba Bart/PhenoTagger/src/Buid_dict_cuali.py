# -*- coding: utf-8 -*-
"""Diccionario para ontologías cualitativas (compatible con PhenoTagger)
- Filtra nodos anónimos (blank nodes)
- Restringe por namespaces permitidos (configurable)
- Limpia is_a y genera los 6 archivos esperados por PhenoTagger
"""

import re
import rdflib
from rdflib.namespace import RDF, RDFS, OWL, SKOS
import json, os, argparse
from collections import defaultdict

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer

# --- NLTK ---
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('wordnet', quiet=True)
lemmatizer = WordNetLemmatizer()

# Namespaces útiles (podés sumar más si tu ontología los usa)
QUALI = rdflib.Namespace("http://www.semanticweb.org/emilio/ontologies/2024/5/untitled-ontology-27#")
OBOINOWL = rdflib.Namespace("http://www.geneontology.org/formats/oboInOwl#")

# --------------------- utilidades de texto ---------------------
def split_camel(s: str) -> str:
    s = re.sub(r'[_/]+', ' ', s)                   # _ y / a espacio
    s = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', s)     # camelCase -> camel Case
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def get_wordnet_pos(tb):
    if tb.startswith('J'): return wordnet.ADJ
    if tb.startswith('V'): return wordnet.VERB
    if tb.startswith('N'): return wordnet.NOUN
    if tb.startswith('R') or tb == 'IN': return wordnet.ADV
    return wordnet.NOUN

def tokenize_and_lemmatize(text):
    text = split_camel(str(text)).lower()
    tokens = word_tokenize(text)
    pos = nltk.pos_tag(tokens)
    lemmas = [lemmatizer.lemmatize(tok, get_wordnet_pos(tag)) for tok, tag in pos]
    return ' '.join(tokens), ' '.join(lemmas)

def get_class_label(g: rdflib.Graph, c: rdflib.term.Identifier) -> str:
    for p in (RDFS.label, SKOS.prefLabel):
        v = g.value(c, p)
        if v: return str(v)
    u = str(c)
    frag = u.split('#')[-1] if '#' in u else u.split('/')[-1]
    return split_camel(frag)

# --------------------- filtrado de URIs ---------------------
def make_uri_filter(allowed_ns):
    """Devuelve función que acepta solo URIRef dentro de namespaces permitidos (si se definen)."""
    def _is_valid(u):
        if not isinstance(u, rdflib.term.URIRef):
            return False
        if not allowed_ns:
            return True
        su = str(u)
        return any(su.startswith(ns) for ns in allowed_ns)
    return _is_valid

# --------------------- raíces y recorrido ---------------------
def find_root_classes(g: rdflib.Graph, is_valid_uri):
    """Clases de nivel superior (sin superclase o solo owl:Thing), filtradas por URI válida."""
    classes = (set(g.subjects(RDF.type, OWL.Class)) |
               set(g.subjects(RDF.type, RDFS.Class)))
    classes = {c for c in classes if is_valid_uri(c)}
    roots = set()
    for c in classes:
        supers = {s for s in g.objects(c, RDFS.subClassOf) if s not in (OWL.Thing, OWL.Nothing)}
        supers = {s for s in supers if is_valid_uri(s)}
        if not supers:
            roots.add(c)
        elif supers == {OWL.Thing}:
            roots.add(c)
    return roots

def get_all_classes(g: rdflib.Graph, root_uris, is_valid_uri):
    if root_uris and root_uris != ['None']:
        roots = [rdflib.URIRef(r) for r in root_uris if is_valid_uri(rdflib.URIRef(r))]
    else:
        roots = list(find_root_classes(g, is_valid_uri))
        print(f"⚠️  Usando raíces automáticas (owl:Thing): {len(roots)} encontradas")

    seen, q, out = set(), list(roots), set()
    while q:
        cur = q.pop(0)
        if cur in seen: 
            continue
        if not is_valid_uri(cur):
            continue
        seen.add(cur); out.add(cur)
        for sub in g.subjects(RDFS.subClassOf, cur):
            if sub not in seen and is_valid_uri(sub):
                q.append(sub)
    return out

# --------------------- construcción del diccionario ---------------------
def build_dict(rdf_path, output_dir, rootnodes, allowed_ns):
    g = rdflib.Graph()
    # Autodetecta formato; si falla, intenta RDF/XML vs Turtle
    try:
        g.parse(rdf_path)
    except Exception:
        fmt = 'application/rdf+xml' if rdf_path.lower().endswith(('.rdf', '.owl', '.xml')) else 'turtle'
        g.parse(rdf_path, format=fmt)

    os.makedirs(output_dir, exist_ok=True)
    is_valid_uri = make_uri_filter(allowed_ns)

    all_nodes = get_all_classes(g, rootnodes, is_valid_uri)
    print(f"✔ Clases identificadas: {len(all_nodes)}")

    # Propiedades con posibles términos/sinónimos
    data_props = [
        RDFS.label, SKOS.altLabel, OBOINOWL.hasExactSynonym,
        QUALI.name, QUALI.title, QUALI.description, QUALI.conclusion,
        QUALI.thematicCore, QUALI.strategyTechniqueObjective, QUALI.patternType
    ]

    dic_terms = {}
    obo_like = {}
    vocab_ids = []

    for i, cls in enumerate(sorted(all_nodes, key=lambda x: str(x))):
        cls_uri = str(cls)
        label = get_class_label(g, cls)
        print(f"Procesando ({i+1}/{len(all_nodes)}): {label}")

        vocab_ids.append(cls_uri)

        # nombre principal
        main_ori, main_lem = tokenize_and_lemmatize(label)
        dic_terms[main_ori] = len(main_ori.split())
        dic_terms[main_lem] = len(main_lem.split())

        # sinónimos (evita duplicar el principal)
        seen_syn = set([main_ori.lower(), main_lem.lower()])
        synonyms = []
        for p in data_props:
            for o in g.objects(cls, p):
                t = str(o).strip()
                if not t:
                    continue
                syn_ori, syn_lem = tokenize_and_lemmatize(t)
                if syn_ori.lower() in seen_syn:
                    continue
                seen_syn.update([syn_ori.lower(), syn_lem.lower()])
                synonyms.append([syn_ori, syn_lem])
                dic_terms[syn_ori] = len(syn_ori.split())
                dic_terms[syn_lem] = len(syn_lem.split())

        # is_a (solo URIs válidas, no Thing/Nothing)
        is_a = []
        for sc in g.objects(cls, RDFS.subClassOf):
            if sc in (OWL.Thing, OWL.Nothing):
                continue
            if is_valid_uri(sc):
                is_a.append(str(sc))

        obo_like[cls_uri] = {
            'name': [main_ori, main_lem],
            'alt_id': [str(a) for a in g.objects(cls, OBOINOWL.hasAlternativeId)],
            'def': str(g.value(cls, RDFS.comment) or ""),
            'synonym': synonyms,
            'xref': [str(x) for x in g.objects(cls, OBOINOWL.hasDbXref)],
            'is_a': is_a,
            'relations': {},
            'is_obsolete': "true" if g.value(cls, OWL.deprecated) else "false",
        }

    # --- salidas con nombres que espera PhenoTagger ---
    with open(os.path.join(output_dir, 'lable.vocab'), 'w', encoding='utf-8') as f:
        f.write("\n".join(vocab_ids + ["HP:None"]))   # etiqueta negativa exacta

    with open(os.path.join(output_dir, 'noabb_lemma.dic'), 'w', encoding='utf-8') as f:
        for term, _ in sorted(dic_terms.items(), key=lambda x: (x[1], x[0])):
            if term:
                f.write(term + "\n")

    with open(os.path.join(output_dir, 'obo.json'), 'w', encoding='utf-8') as f:
        json.dump(obo_like, f, indent=2, ensure_ascii=False)

    generate_mappings(obo_like, output_dir)
    print("✅ Diccionario listo.")

# --------------------- mapeos ---------------------
def generate_mappings(obo_like, output_dir):
    word2ids = defaultdict(list)
    id2words = defaultdict(list)
    alt_map = {}

    for cid, data in obo_like.items():
        all_terms = {data['name'][0], data['name'][1]}
        for s in data['synonym']:
            all_terms.update(s)

        all_terms = {t for t in all_terms if t}  # quita vacíos

        for t in all_terms:
            if cid not in word2ids[t]:
                word2ids[t].append(cid)
        id2words[cid] = sorted(all_terms)

        alt_map[cid] = cid
        for alt in data.get('alt_id', []):
            alt_map[alt] = cid

    with open(os.path.join(output_dir, 'word_id_map.json'), 'w', encoding='utf-8') as f:
        json.dump(word2ids, f, indent=2, ensure_ascii=False)
    with open(os.path.join(output_dir, 'id_word_map.json'), 'w', encoding='utf-8') as f:
        json.dump(id2words, f, indent=2, ensure_ascii=False)
    with open(os.path.join(output_dir, 'alt_hpoid.json'), 'w', encoding='utf-8') as f:
        json.dump(alt_map, f, indent=2, ensure_ascii=False)

# --------------------- CLI ---------------------
if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="Construir diccionario (OWL/RDF) compatible con PhenoTagger")
    ap.add_argument('-i','--input', required=True, help='Archivo OWL/RDF/Turtle (ontología)')
    ap.add_argument('-o','--output', default='dict_qualitative/', help='Carpeta de salida')
    ap.add_argument('-r','--rootnode', nargs='+', default=['None'],
                    help="URIs raíz; usa 'None' para detectar raíces automáticamente")
    ap.add_argument('-a','--allow-ns', nargs='*', default=[
        "http://www.semanticweb.org/emilio/ontologies/2024/5/untitled-ontology-27#",
        "http://www.semanticweb.org/emilio/ontologies/2024/7/untitled-ontology-52#",
    ], help="Prefijos de namespaces permitidos; deja vacío para aceptar todos")
    args = ap.parse_args()

    print("\n🔍 Construyendo diccionario…")
    print(f"📁 Entrada: {args.input}")
    print(f"📂 Salida:  {args.output}")
    print(f"🌱 Roots:   {args.rootnode}")
    print(f"📚 Namespaces permitidos: {args.allow_ns}\n")

    build_dict(args.input, args.output, args.rootnode, args.allow_ns)
