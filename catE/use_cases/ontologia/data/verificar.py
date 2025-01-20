import pandas as pd

# Función para cargar los nodos de un archivo CSV
def load_nodes(file_path):
    try:
        data = pd.read_csv(file_path, header=None)
        if data.shape[1] < 2:
            print(f"El archivo {file_path} no tiene al menos dos columnas.")
            return set()
        # Retornar la unión de la primera y segunda columna como conjunto de nodos
        return set(data[0]).union(set(data[1]))
    except Exception as e:
        print(f"Error al cargar nodos desde {file_path}: {e}")
        return set()

# Función para cargar los nodos del grafo
def load_graph_nodes(graph_path):
    try:
        data = pd.read_csv(graph_path, sep="\t", header=None)
        if data.shape[1] < 3:
            print(f"El archivo {graph_path} no tiene al menos tres columnas.")
            return set()
        # Retornar la unión de las columnas de nodos del grafo
        return set(data[0]).union(set(data[2]))
    except Exception as e:
        print(f"Error al cargar nodos desde {graph_path}: {e}")
        return set()

# Archivos de entrada
graph_path = "D:/mai/catE/use_cases/ontologia/data/ontologia.cat.edgelist"
test_file_path = "D:/mai/catE/use_cases/ontologia/data/test.csv"
valid_file_path = "D:/mai/catE/use_cases/ontologia/data/valid.csv"

# Cargar los nodos de los archivos
graph_nodes = load_graph_nodes(graph_path)
test_nodes = load_nodes(test_file_path)
valid_nodes = load_nodes(valid_file_path)

# Verificar nodos faltantes
test_missing = test_nodes - graph_nodes
valid_missing = valid_nodes - graph_nodes

# Imprimir resultados
print("Nodos faltantes en el grafo:")
if test_missing:
    print(f"- Desde el archivo de prueba ({len(test_missing)} nodos):")
    print(test_missing)
else:
    print("- No faltan nodos desde el archivo de prueba.")

if valid_missing:
    print(f"- Desde el archivo de validación ({len(valid_missing)} nodos):")
    print(valid_missing)
else:
    print("- No faltan nodos desde el archivo de validación.")

