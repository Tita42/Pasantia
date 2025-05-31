import torch

# Cargar el archivo
data = torch.load("models/ontologiaEL_False_dim200_bs8192_lr0.0001_negs2_margin1.0_lossnormal.model.pt", map_location="cpu")

# Imprimir las claves
print("Claves disponibles:", data.keys())

# Inspeccionar detalles
print("Tamaño del modelo:", type(data["model_state_dict"]))
print("Ejemplo de node_to_id:", list(data["node_to_id"].items())[:5])
print("Ejemplo de ontology_classes:", data["ontology_classes"][:5])
print("Ejemplo de ontology_classes_idxs:", data["ontology_classes_idxs"][:5])
print("Configuración:", data["config"])
