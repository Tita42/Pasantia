import torch
import pandas as pd
import numpy as np

# Cargar archivo .pt
data = torch.load("models/ontologiaEL_False_dim200_bs8192_lr0.0001_negs2_margin1.0_lossnormal.model.pt", map_location="cpu")

state_dict = data["model_state_dict"] #Contiene los embeddings en un OrderedDict
node_to_id = data["node_to_id"]
id_to_node = {v: k for k, v in node_to_id.items()}
class_idxs = data["ontology_classes_idxs"].tolist()
embedding_tensor = state_dict["entity_representations.0._embeddings.weight"]  # [N, emb_dim]

# Extraer solo las clases
rows = []
for idx in class_idxs:
    uri = id_to_node[idx]
    vector = embedding_tensor[idx].cpu().numpy()
    rows.append([uri] + vector.tolist())

# Guardar CSV
df = pd.DataFrame(rows, columns=["uri"] + [f"x{i}" for i in range(embedding_tensor.size(1))])
df.to_csv("ontology_embeddings.csv", index=False)
