# procesar_todo.py
import os
from extractor import data_manager

carpeta = "datos_dat"
archivos = [f for f in os.listdir(carpeta) if f.endswith('.dat')]

print(f"Detectados {len(archivos)} archivos. Iniciando carga...")

for archivo in archivos:
    ruta = os.path.join(carpeta, archivo)
    if data_manager.procesar_dat(ruta):
        print(f"✅ Procesado: {archivo}")
    else:
        print(f"❌ Error en: {archivo}")

print("¡Base de datos actualizada!")