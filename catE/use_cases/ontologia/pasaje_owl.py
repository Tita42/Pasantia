from rdflib import Graph, URIRef, RDFS
import pandas as pd

def csv_to_ontology(csv_path, output_owl):
    df = pd.read_csv(csv_path)
    g = Graph()

    for _, row in df.iterrows():
        head = URIRef(row['head'])
        tail = URIRef(row['tail'])
        g.add((head, RDFS.subClassOf, tail))

    g.serialize(destination=output_owl, format='xml')
    print(f"Ontología generada en {output_owl} con {len(df)} relaciones.")

if __name__ == "__main__":
    csv_to_ontology("subsumption_edges.csv", "nueva_ontologia.owl")
