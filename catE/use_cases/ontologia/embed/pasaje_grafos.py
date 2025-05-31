import pandas as pd
import numpy as np
from tqdm import tqdm

# Cargar embeddings
df = pd.read_csv("ontology_embeddings.csv")
vectors = df.drop(columns=["uri"]).to_numpy()
uris = df["uri"].tolist()

# Función OrderE: dirección jerárquica A ⊑ B
def order_score(h, t):
    return -np.linalg.norm(np.maximum(0, t - h))**2

# Umbral (ajustalo si querés más o menos precisión)
threshold = -0.7

# Generar relaciones sin score ni top-k
edges = []
for i, h in tqdm(enumerate(vectors), total=len(vectors), desc="Construyendo jerarquía"):
    for j, t in enumerate(vectors):
        if i == j:
            continue
        score = order_score(h, t)
        if score > threshold:
            edges.append((uris[i], uris[j]))

# Guardar como CSV (sin score)
edges_df = pd.DataFrame(edges, columns=["head", "tail"])
edges_df.to_csv("subsumption_edges.csv", index=False)

print(f"✔️ Relaciones generadas: {len(edges_df)}")
