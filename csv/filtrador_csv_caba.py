import pandas as pd
import os

# Obtener la ruta del directorio actual del script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construir la ruta completa al archivo CSV
csv_path = os.path.join(current_dir, "salas_cine.csv")

# Leer el CSV original
df = pd.read_csv(csv_path, encoding="utf-8")

# Filtrar solo las filas donde la columna 'provincia' sea igual a "Ciudad Autónoma de Buenos Aires"
df_filtrado = df[df["provincia"] == "Ciudad Autónoma de Buenos Aires"]

# Guardar el resultado en un nuevo CSV
df_filtrado.to_csv("salas_cine_filtrado.csv", index=False, encoding="utf-8")
