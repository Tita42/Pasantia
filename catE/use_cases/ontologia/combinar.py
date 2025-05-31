from rdflib import Graph, RDFS
from rdflib.term import URIRef

# === Rutas de entrada y salida ===
original_owl = "data/untitled-ontology-52.owl"
nueva_owl = "embed/nueva_ontologia.owl"
salida_owl = "ontologia_combinada.owl"

# === Cargar grafos ===
gor = Graph()
gor.parse(original_owl, format="xml")

gnew = Graph()
gnew.parse(nueva_owl, format="xml")

# === Extraer SubClassOf originales ===
original_subs = set((s, o) for s, _, o in gor.triples((None, RDFS.subClassOf, None)))

# === Agregar solo nuevas SubClassOf ===
nuevos_agregados = 0
for s, _, o in gnew.triples((None, RDFS.subClassOf, None)):
    if (s, o) not in original_subs:
        gor.add((s, RDFS.subClassOf, o))
        nuevos_agregados += 1

# === Guardar el grafo combinado ===
gor.serialize(salida_owl, format="xml")

print(f" Ontología combinada guardada en {salida_owl}")
print(f" Relaciones SubClassOf agregadas desde embedding: {nuevos_agregados}")
