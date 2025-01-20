from owlready2 import get_ontology

# Cargar la ontología
onto = get_ontology(r"D:\mai\catE\use_cases\ontologia\data\ontologia.owl").load()

# Crear el archivo de ancestros inferidos
with open("inferred_ancestors.txt", "w") as f:
    for cls in onto.classes():
        # Obtener ancestros inferidos
        ancestors = cls.ancestors()  # Incluye la clase actual y todos los ancestros
        ancestors = [ancestor.name for ancestor in ancestors if ancestor.name]
        # Escribir en el archivo
        f.write(f"{cls.name},{','.join(ancestors)}\n")
