# -*- coding: utf-8 -*-
"""Script adaptado para ontologías de metodología cualitativa
@author: Maite Martínez
@adaptado_de: luol2 (script original para HPO)
"""

import rdflib
from rdflib.namespace import RDF, RDFS, OWL, SKOS
import json
import os
import argparse
from collections import defaultdict

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer

# Configuración inicial
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('wordnet', quiet=True)

lemmatizer = WordNetLemmatizer()

# Namespaces personalizados para tu ontología
QUALI = rdflib.Namespace("http://www.semanticweb.org/emilio/ontologies/2024/5/untitled-ontology-27#")
OBOINOWL = rdflib.Namespace("http://www.geneontology.org/formats/oboInOwl#")

def get_wordnet_pos(treebank_tag):
    """Adaptado para términos de ciencias sociales"""
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R') or treebank_tag == 'IN':
        return wordnet.ADV
    else:
        return wordnet.NOUN  # Por defecto sustantivo

def tokenize_and_lemmatize(text):
    """Procesamiento especializado para términos metodológicos"""
    text = str(text).replace('_', ' ').replace('-', ' - ')
    tokens = word_tokenize(text.strip().lower())
    pos_tags = nltk.pos_tag(tokens)
    lemmas = [lemmatizer.lemmatize(token[0], get_wordnet_pos(token[1])) for token in pos_tags]
    return ' '.join(tokens), ' '.join(lemmas)

def get_all_classes(graph, rootnodes=None):
    """Obtiene clases con manejo especial de técnicas cualitativas"""
    # Definir propiedades de interés para tu dominio
    core_properties = {RDFS.subClassOf, QUALI.answersToQuestion, QUALI.appliesTechnique}
    
    if rootnodes == ['None'] or not rootnodes:
        return set(graph.subjects(RDF.type, OWL.Class)) | set(graph.subjects(RDF.type, RDFS.Class))

    # Construir árbol de relaciones incluyendo object properties específicas
    hierarchy = defaultdict(list)
    for s, p, o in graph.triples((None, None, None)):
        if p in core_properties:
            hierarchy[str(o)].append(str(s))

    visited = set()
    
    def dfs(node):
        nonlocal visited
        if node in visited:
            return
        visited.add(node)
        for child in hierarchy.get(node, []):
            dfs(child)

    for rn in rootnodes:
        dfs(rn)

    return {rdflib.URIRef(uri) for uri in visited if uri.startswith("http://www.semanticweb.org/emilio/ontologies/2024/5/untitled-ontology-27#")}

def build_dict(rdf_path, output_dir, rootnodes):
    """Función principal con adaptaciones para metodología cualitativa"""
    g = rdflib.Graph()
    
    # Registrar namespaces
    g.bind("quali", QUALI)
    g.bind("oboInOwl", OBOINOWL)
    
    g.parse(rdf_path)
    
    os.makedirs(output_dir, exist_ok=True)

    all_nodes = get_all_classes(g, rootnodes)
    print(f"✔ Clases relevantes identificadas: {len(all_nodes)}")

    # Propiedades para extraer términos (ampliado para tu dominio)
    data_properties = [
        RDFS.label,
        QUALI.name,
        QUALI.title,
        QUALI.description,
        QUALI.conclusion,
        QUALI.thematicCore,
        QUALI.strategyTechniqueObjective,
        QUALI.patternType,
        SKOS.altLabel,
        OBOINOWL.hasExactSynonym
    ]

    hpo_dict = {}
    hpo_obo = {}
    vocab_ids = []

    for i, cls in enumerate(all_nodes):
        print(f"Procesando: {i+1}/{len(all_nodes)} - {str(cls).split('/')[-1]}", end='\r')

        hpoid = str(cls)
        vocab_ids.append(hpoid)

        # 1. Nombre principal
        main_text = None
        for prop in [RDFS.label, QUALI.name, QUALI.title]:
            main_text = g.value(cls, prop)
            if main_text:
                break

        if not main_text:
            continue

        name_ori, name_lemma = tokenize_and_lemmatize(main_text)
        hpo_dict[name_ori] = len(name_ori.split())
        hpo_dict[name_lemma] = len(name_lemma.split())

        # 2. Sinónimos y términos relacionados
        synonyms = []
        for prop in data_properties:
            for o in g.objects(cls, prop):
                if o != main_text:  # Evitar duplicados
                    syn_ori, syn_lemma = tokenize_and_lemmatize(o)
                    synonyms.append([syn_ori, syn_lemma])
                    hpo_dict[syn_ori] = len(syn_ori.split())
                    hpo_dict[syn_lemma] = len(syn_lemma.split())

        # 3. Relaciones metodológicas clave
        relations = defaultdict(list)
        for pred in [QUALI.appliesTechnique, QUALI.hasQuestion, QUALI.hasResearcher]:
            for obj in g.objects(cls, pred):
                relations[str(pred)].append(str(obj))

        # 4. Construir entrada en el diccionario
        hpo_obo[hpoid] = {
            'name': [name_ori, name_lemma],
            'alt_id': [str(a) for a in g.objects(cls, OBOINOWL.hasAlternativeId)],
            'def': str(g.value(cls, QUALI.description)) or "",
            'synonym': synonyms,
            'xref': [str(x) for x in g.objects(cls, OBOINOWL.hasDbXref)],
            'is_a': [str(o) for o in g.objects(cls, RDFS.subClassOf)],
            'relations': dict(relations),
            'is_obsolete': str(g.value(cls, OWL.deprecated)) or "false",
            'technique_type': str(g.value(cls, QUALI.techniqueType)) if g.value(cls, QUALI.techniqueType) else ""
        }

    # Guardar archivos (igual que antes pero con mejor formato)
    with open(os.path.join(output_dir, 'lable.vocab'), 'w', encoding='utf-8') as f:
        f.write("\n".join(vocab_ids + ["QUALI:None"]))  # Etiqueta negativa específica

    with open(os.path.join(output_dir, 'noabb_lemma.dic'), 'w', encoding='utf-8') as f:
        for term, _ in sorted(hpo_dict.items(), key=lambda x: (x[1], x[0])):
            f.write(f"{term}\n")

    with open(os.path.join(output_dir, 'obo.json'), 'w', encoding='utf-8') as f:
        json.dump(hpo_obo, f, indent=2, ensure_ascii=False)

    # Generar mapeos mejorados
    generate_mappings(hpo_obo, output_dir)

def generate_mappings(hpo_obo, output_dir):
    """Genera archivos de mapeo con información enriquecida"""
    word_hpoid = defaultdict(list)
    hpoid_word = defaultdict(list)
    alt_hpoid = {}

    for hpoid, data in hpo_obo.items():
        # Todas las variantes del término
        all_terms = {data['name'][0], data['name'][1]}
        for syn_pair in data['synonym']:
            all_terms.update(syn_pair)
        
        # Mapeo término -> ID
        for term in all_terms:
            if hpoid not in word_hpoid[term]:
                word_hpoid[term].append(hpoid)
        
        # Mapeo ID -> términos
        hpoid_word[hpoid] = list(all_terms)
        
        # IDs alternativos
        alt_hpoid[hpoid] = hpoid
        for alt in data.get('alt_id', []):
            alt_hpoid[alt] = hpoid

    # Guardar mapeos
    with open(os.path.join(output_dir, 'word_id_map.json'), 'w', encoding='utf-8') as f:
        json.dump(word_hpoid, f, indent=2, ensure_ascii=False)

    with open(os.path.join(output_dir, 'id_word_map.json'), 'w', encoding='utf-8') as f:
        json.dump(hpoid_word, f, indent=2, ensure_ascii=False)

    with open(os.path.join(output_dir, 'alt_hpoid.json'), 'w', encoding='utf-8') as f:
        json.dump(alt_hpoid, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Construir diccionario para ontología cualitativa")
    parser.add_argument('-i', '--input', required=True, help="Archivo RDF de entrada (ej. metodologia.ttl)")
    parser.add_argument('-o', '--output', default='dict_qualitative/', help="Directorio de salida")
    parser.add_argument('-r', '--rootnode', nargs='+', 
                       default=["http://www.semanticweb.org/emilio/ontologies/2024/5/untitled-ontology-27#"],
                       help="Nodos raíz (ej. 'http.../DataCollection')")
    args = parser.parse_args()

    print("\n🔍 Construyendo diccionario para metodología cualitativa...")

    build_dict(args.input, args.output, args.rootnode)

    print("\n✅ ¡Diccionario generado con éxito!")

    print(f"📁 Archivos guardados en: {args.output}")
