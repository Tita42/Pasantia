from rdflib import Graph, RDFS
import pandas as pd

# === CONFIGURACIÓN ===
original_owl = "data/untitled-ontology-52.owl"
nueva_owl = "embed/nueva_ontologia.owl"

# === FUNCIONES ===
def extraer_subclassof(graph_path):
    g = Graph()
    g.parse(graph_path, format="xml")
    return set((str(s), str(o)) for s, _, o in g.triples((None, RDFS.subClassOf, None)))

# === CARGA DE ONTOLOGÍAS ===
original_axioms = extraer_subclassof(original_owl)
nueva_axioms = extraer_subclassof(nueva_owl)

# === COMPARACIÓN ===
comunes = original_axioms & nueva_axioms
nuevas = nueva_axioms - original_axioms
perdidas = original_axioms - nueva_axioms

# === REPORTES ===
pd.DataFrame(comunes, columns=["head", "tail"]).to_csv("relaciones_comunes.csv", index=False)
pd.DataFrame(nuevas, columns=["head", "tail"]).to_csv("relaciones_nuevas.csv", index=False)
pd.DataFrame(perdidas, columns=["head", "tail"]).to_csv("relaciones_perdidas.csv", index=False)

print(f"✅ Relaciones comunes: {len(comunes)}")
print(f"➕ Relaciones nuevas: {len(nuevas)}")
print(f"❌ Relaciones perdidas: {len(perdidas)}")
