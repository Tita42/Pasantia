import pandas as pd
from rdflib import Graph, URIRef, RDFS
import argparse

def load_valid_uris(txt_path):
    with open(txt_path, "r") as f:
        uris = {URIRef(line.strip()) for line in f if line.strip()}
    print(f"✔️ Clases válidas cargadas: {len(uris)}")
    return uris

def csv_to_filtered_ontology(csv_path, output_owl, valid_uris):
    df = pd.read_csv(csv_path)
    g = Graph()
    count = 0
    descartadas = 0

    for _, row in df.iterrows():
        head = URIRef(row['head'])
        tail = URIRef(row['tail'])
        if head in valid_uris and tail in valid_uris:
            g.add((head, RDFS.subClassOf, tail))
            count += 1
        else:
            descartadas += 1

    g.serialize(destination=output_owl, format='xml')
    print(f"✔️ Ontología filtrada guardada en {output_owl}")
    print(f"   Relaciones agregadas: {count}")
    print(f"   Relaciones descartadas: {descartadas}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filtrar relaciones válidas según clases originales y generar OWL.")
    parser.add_argument("--csv", required=True, help="Ruta al archivo CSV con relaciones")
    parser.add_argument("--classes", required=True, help="Archivo de texto con URIs válidas (una por línea)")
    parser.add_argument("--out", required=True, help="Ruta de salida para la nueva ontología OWL")

    args = parser.parse_args()

    valid_uris = load_valid_uris(args.classes)
    csv_to_filtered_ontology(args.csv, args.out, valid_uris)

