import pandas as pd
import os

def clean_csv(input_file, output_file):
    try:
        # Leer el archivo CSV con separador personalizado (coma)
        df = pd.read_csv(input_file, header=None, sep=',')

        # Eliminar caracteres < y > en todas las celdas
        df = df.applymap(lambda x: x.replace('<', '').replace('>', '') if isinstance(x, str) else x)

        # Guardar el archivo limpiado
        df.to_csv(output_file, index=False, header=False)
        print(f"Archivo limpio generado: {output_file}")
    except Exception as e:
        print(f"Error al procesar {input_file}: {e}")

if __name__ == "__main__":
    # Archivos de entrada y salida
    files_to_clean = {
        "valid.csv": "valid_cleaned.csv",
        "test.csv": "test_cleaned.csv"
    }

    for input_file, output_file in files_to_clean.items():
        if os.path.exists(input_file):
            clean_csv(input_file, output_file)
        else:
            print(f"Archivo no encontrado: {input_file}")
