# -*- coding: utf-8 -*-
"""
PhenoTagger_tagging.py (versión simplificada para este proyecto)
- Import opcional de NegBio 
- Usa el diccionario ../diccionarios/*
- Carga el modelo entrenado con BERT base cased: ../models/bertbase_PT.h5
- Umbral y opciones ajustadas para metodología cualitativa
"""

import argparse
import os
import time
import json
import re

from nn_model import bioTag_CNN, bioTag_BERT
from dic_ner import dic_ont
from tagging_text import bioTag

# NegBio (negation/uncertainty) es opcional
try:
    from negbio2.negbio_run import negbio_load, negbio_main
    _HAS_NEGBIO = True
except Exception:
    _HAS_NEGBIO = False

import bioc
import tensorflow as tf

gpu = tf.config.list_physical_devices('GPU')
print("Num GPUs Available: ", len(gpu))
if len(gpu) > 0:
    tf.config.experimental.set_memory_growth(gpu[0], True)


def PubTator_Converter(infile, outfile, biotag_dic, nn_model, para_set):
    with open(infile, 'r', encoding='utf-8') as fin:
        with open(outfile, 'w', encoding='utf8') as fout:
            title = ''
            abstract = ''
            for line in fin:
                line = line.rstrip()
                p_title = re.compile(r'^([0-9]+)\|t\|(.*)$')
                p_abstract = re.compile(r'^([0-9]+)\|a\|(.*)$')
                if p_title.search(line):  # title
                    m = p_title.match(line)
                    pmid = m.group(1)
                    title = m.group(2)
                    fout.write(pmid + "|t|" + title + "\n")
                elif p_abstract.search(line):  # abstract
                    m = p_abstract.match(line)
                    pmid = m.group(1)
                    abstract = m.group(2)
                    fout.write(pmid + "|a|" + abstract + "\n")
                else:  # annotation trigger -> procesamos título+abstract acumulados
                    intext = (title + ' ' + abstract).strip()
                    tag_result = bioTag(
                        intext,
                        biotag_dic,
                        nn_model,
                        onlyLongest=para_set['onlyLongest'],
                        abbrRecog=para_set['abbrRecog'],
                        Threshold=para_set['ML_Threshold']
                    )

                    for ele in tag_result:
                        start = ele[0]
                        last = ele[1]
                        mention = intext[int(ele[0]):int(ele[1])]
                        _type = 'Phenotype'   # etiqueta genérica que usa PhenoTagger
                        _id = ele[2]
                        score = ele[3]
                        fout.write(f"{pmid}\t{start}\t{last}\t{mention}\t{_type}\t{_id}\t{score}\n")
                    fout.write('\n')
                    title = ''
                    abstract = ''


def BioC_Converter(infile, outfile, biotag_dic, nn_model, para_set):
    with open(infile, 'r', encoding='utf-8') as fin:
        with open(outfile, 'w', encoding='utf8') as fout:
            collection = bioc.load(fin)
            for document in collection.documents:
                mention_num = 0
                for passage in document.passages:
                    passage_offset = passage.offset
                    tag_result = bioTag(
                        passage.text,
                        biotag_dic,
                        nn_model,
                        onlyLongest=para_set['onlyLongest'],
                        abbrRecog=para_set['abbrRecog'],
                        Threshold=para_set['ML_Threshold']
                    )

                    for ele in tag_result:
                        bioc_note = bioc.BioCAnnotation()
                        bioc_note.id = str(mention_num)
                        mention_num += 1
                        bioc_note.infons['identifier'] = ele[2]
                        bioc_note.infons['type'] = "Phenotype"
                        bioc_note.infons['score'] = ele[3]
                        start = int(ele[0])
                        last = int(ele[1])
                        loc = bioc.BioCLocation(offset=str(passage_offset + start), length=str(last - start))
                        bioc_note.locations.append(loc)
                        bioc_note.text = passage.text[start:last]
                        passage.annotations.append(bioc_note)
            bioc.dump(collection, fout, pretty_print=True)


def PubTator_negbio(pipeline, argv, infile, outpath):
    """
    Convierte PubTator -> BioC, corre NegBio, y vuelve a PubTator con tags de negación/incertidumbre.
    Solo se usa si para_set['negation'] == True y _HAS_NEGBIO == True.
    """
    fin = open(infile, 'r', encoding='utf-8')
    all_in = fin.read().strip().split('\n\n')
    fin.close()

    collection = bioc.BioCCollection()
    for doc in all_in:
        if not doc.strip():
            continue
        lines = doc.split('\n')
        seg1 = lines[0].split('|t|')
        pmid = seg1[0]
        seg2 = lines[1].split('|a|') if len(lines) > 1 else ['','']
        text_in = (seg1[1] + ' ' + (seg2[1] if len(seg2) > 1 else '')).strip()

        document = bioc.BioCDocument()
        document.id = pmid

        passage = bioc.BioCPassage()
        passage.offset = 0
        passage.text = text_in
        document.add_passage(passage)

        mention_num = 0
        for i in range(2, len(lines)):
            if not lines[i].strip():
                continue
            ele = lines[i].split('\t')
            if len(ele) < 7:
                continue
            bioc_node = bioc.BioCAnnotation()
            bioc_node.id = str(mention_num)
            bioc_node.infons['identifier'] = ele[5]
            bioc_node.infons['type'] = "Phenotype"
            bioc_node.infons['score'] = ele[6]
            start = int(ele[1])
            last = int(ele[2])
            loc = bioc.BioCLocation(offset=str(passage.offset + start), length=str(last - start))
            bioc_node.locations.append(loc)
            bioc_node.text = passage.text[start:last]
            passage.annotations.append(bioc_node)
            mention_num += 1

        collection.add_document(document)

    tmp_xml = os.path.join(outpath, 'tmp.xml')
    tmp_neg2_xml = os.path.join(outpath, 'tmp.neg2.xml')

    with open(tmp_xml, 'w') as fp:
        bioc.dump(collection, fp)

    negbio_main(pipeline, argv, tmp_xml, outpath)

    # leer resultados negbio y mapear al pubtator original
    fin = open(tmp_neg2_xml, 'r', encoding='utf-8')
    neg2_results = {}  # {pmid:{'0':'neg', '1':'uncertainty', ...}}
    collection = bioc.load(fin)
    fin.close()

    for document in collection.documents:
        pmid = document.id
        _mention = {}
        for passage in document.passages:
            for men_node in passage.annotations:
                if 'uncertainty' in men_node.infons.keys():
                    _mention[men_node.id] = 'uncertainty'
                elif 'negation' in men_node.infons.keys():
                    _mention[men_node.id] = 'negation'
                else:
                    _mention[men_node.id] = 'positive'
        neg2_results[pmid] = _mention

    fin = open(infile, 'r', encoding='utf-8')
    all_in = fin.read().strip().split('\n\n')
    fin.close()

    seg = infile.split('.')
    out_pub = '.'.join(seg[:-1]) + '.neg2.' + seg[-1]
    with open(out_pub, 'w', encoding='utf-8') as fout:
        for doc in all_in:
            if not doc.strip():
                continue
            lines = doc.split('\n')
            j = 0
            fout.write(lines[0] + '\n')
            if len(lines) > 1:
                fout.write(lines[1] + '\n')

            for i in range(2, len(lines)):
                if not lines[i].strip():
                    continue
                segl = lines[i].split('\t')
                pmid = segl[0]
                tag = neg2_results.get(pmid, {}).get(str(j), 'positive')
                fout.write(lines[i] + '\t' + tag + '\n')
                j += 1
            fout.write('\n')

    # limpiar temporales
    try:
        os.remove(tmp_xml)
    except Exception:
        pass
    try:
        os.remove(tmp_neg2_xml)
    except Exception:
        pass


def phenotagger_tag(infolder, para_set, outfolder):
    # === rutas de tu diccionario ===
    ontfiles = {
        'dic_file': '../diccionarios/noabb_lemma.dic',
        'word_hpo_file': '../diccionarios/word_id_map.json',
        'hpo_word_file': '../diccionarios/id_word_map.json'
    }

    # === configuración del modelo: BERT base cased entrenado por ti ===
    vocabfiles = {
        'labelfile': '../diccionarios/lable.vocab',
        'checkpoint_path': 'bert-base-cased',  # para tokenización/config HF
        'lowercase': False
    }
    modelfile = '../models/bertbase_PT.h5'

    # cargar diccionario y modelo
    print("loading dict!")
    biotag_dic = dic_ont(ontfiles)
    print("load dic done!")

    nn_model = bioTag_BERT(vocabfiles)
    nn_model.load_model(modelfile)

    # NegBio opcional
    if para_set.get('negation', False) and not _HAS_NEGBIO:
        print("⚠️  NegBio no está disponible: se desactiva detección de negaciones.")
        para_set['negation'] = False

    if para_set['negation'] and _HAS_NEGBIO:
        pipeline, argv = negbio_load()

    # tagging
    print("begin tagging........")
    start_time = time.time()

    files = [f for f in os.listdir(infolder) if not f.startswith('.')]
    N = len(files)
    for i, filename in enumerate(files, 1):
        print("Processing:{0}%".format(round((i - 1) * 100 / N)), end="\r")

        in_path = os.path.join(infolder, filename)
        out_path = os.path.join(outfolder, filename)

        # detectar formato
        with open(in_path, 'r', encoding='utf-8') as fin:
            format = ""
            for line in fin:
                if re.search(r'.*<collection>.*', line):
                    format = "BioC"
                    break
                if re.search(r'^([^\|]+)\|[^\|]+\|(.*)', line):
                    format = "PubTator"
                    break

        if format == "PubTator":
            PubTator_Converter(in_path, out_path, biotag_dic, nn_model, para_set)
            if para_set['negation'] and _HAS_NEGBIO:
                PubTator_negbio(pipeline, argv, out_path, outfolder)
        elif format == "BioC":
            BioC_Converter(in_path, out_path, biotag_dic, nn_model, para_set)
            if para_set['negation'] and _HAS_NEGBIO:
                negbio_main(pipeline, argv, out_path, outfolder)
        else:
            # si no es PubTator ni BioC, tratamos el archivo como texto plano y
            # lo convertimos a un documento PubTator mínimo
            with open(in_path, 'r', encoding='utf-8') as fin:
                text = fin.read().strip()
            pmid = os.path.splitext(filename)[0]
            tmp_in = os.path.join(outfolder, f"{pmid}.tmp.pubtator")
            with open(tmp_in, 'w', encoding='utf-8') as fout:
                fout.write(f"{pmid}|t|{pmid}\n{pmid}|a|{text}\n\n")
            PubTator_Converter(tmp_in, out_path, biotag_dic, nn_model, para_set)
            try:
                os.remove(tmp_in)
            except Exception:
                pass

    print('\ntag done:', round(time.time() - start_time, 2), 's')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Etiquetar textos con tu ontología cualitativa')
    parser.add_argument('--infolder', '-i', help="carpeta de entrada", default='../test_in/')
    parser.add_argument('--outfolder', '-o', help="carpeta de salida", default='../test_out/')
    args = parser.parse_args()

    if not os.path.exists(args.outfolder):
        os.makedirs(args.outfolder, exist_ok=True)

    # Parámetros recomendados para tu dominio
    para_set = {
        'model_type': 'bertbase',  # informativo
        'onlyLongest': True,       # conserva solo la mención más larga al solaparse
        'abbrRecog': False,        # pocas abreviaturas en esta ontología
        'negation': False,         # NegBio desactivado (y opcional)
        'ML_Threshold': 0.40,      # umbral algo más permisivo para captar variantes
    }

    phenotagger_tag(args.infolder, para_set, args.outfolder)
    print('The results are in ', args.outfolder)
