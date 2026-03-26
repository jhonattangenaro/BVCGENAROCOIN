import os
base = os.path.dirname(os.path.abspath(__file__))
ruta_data = os.path.join(base, "data")

print(f"--- VERIFICADOR DE RUTAS ---")
print(f"1. Tu script está en: {base}")
print(f"2. Buscando carpeta 'data' en: {ruta_data}")

if os.path.exists(ruta_data):
    archivos = [f for f in os.listdir(ruta_data) if f.upper().endswith('.DAT')]
    print(f"3. ✅ ¡Carpeta encontrada!")
    print(f"4. 📄 Archivos .DAT detectados: {len(archivos)}")
    for a in archivos[:3]: print(f"   - {a}")
else:
    print(f"3. ❌ ERROR: No veo la carpeta 'data'.")
    print(f"   Asegúrate de que la carpeta se llame exactamente 'data' (minúsculas).")