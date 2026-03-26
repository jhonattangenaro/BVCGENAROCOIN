"""
fix_volumen.py
==============
Re-procesa todos los archivos .dat en la carpeta 'datos_dat' y corrige
el campo 'volumen' (efectivo Bs.S) en la tabla 'mercado'.

Formato de línea R|:
  pos 0  → R
  pos 1  → nombre
  pos 2  → símbolo
  pos 3  → apertura
  pos 4  → cierre
  pos 5  → var absoluta
  pos 6  → var %
  pos 7  → mínimo
  pos 8  → máximo
  pos 9  → promedio
  pos 10 → operaciones
  pos 11 → títulos (cantidad acciones)  ← era el error
  pos 12 → efectivo Bs.S                ← el correcto

Uso:
    Coloca este script en la raíz del proyecto (junto a app.py) y ejecuta:
        python fix_volumen.py
"""

import sqlite3
import os
import re

# ── Configuración ──────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(BASE_DIR, "database", "bolsa_datos.db")
DATA_DIR  = os.path.join(BASE_DIR, "datos_dat")


def convertir(valor):
    """Convierte string numérico europeo (1.234,56) a float."""
    if not valor:
        return 0.0
    val = str(valor).strip().replace(' ', '').replace('%', '')
    try:
        if ',' in val and '.' in val:
            val = val.replace('.', '').replace(',', '.')
        elif ',' in val:
            val = val.replace(',', '.')
        return float(val)
    except:
        return 0.0


def fecha_desde_nombre(nombre_archivo):
    match = re.search(r'(\d{8})', nombre_archivo)
    if match:
        f = match.group(1)
        if int(f[:4]) > 1900:
            return f"{f[:4]}-{f[4:6]}-{f[6:]}"
        else:
            return f"{f[4:]}-{f[2:4]}-{f[:2]}"
    return None


def procesar_dat(ruta_archivo, cursor):
    nombre_archivo = os.path.basename(ruta_archivo)
    fecha = fecha_desde_nombre(nombre_archivo)
    if not fecha:
        print(f"  ⚠️  No se pudo extraer fecha de: {nombre_archivo}")
        return 0

    actualizados = 0
    with open(ruta_archivo, 'r', encoding='latin-1') as fh:
        for linea in fh:
            if not linea.startswith('R|'):
                continue
            partes = linea.strip().split('|')
            if len(partes) < 13:
                continue
            try:
                simbolo  = partes[2].strip()
                # posición 12 = efectivo (monto Bs.S negociado)
                efectivo = convertir(partes[12])

                cursor.execute(
                    "UPDATE mercado SET volumen = ? WHERE fecha = ? AND simbolo = ?",
                    (efectivo, fecha, simbolo)
                )
                if cursor.rowcount > 0:
                    actualizados += 1
            except Exception as ex:
                print(f"  ⚠️  Error en línea ({simbolo}): {ex}")

    return actualizados


def main():
    if not os.path.exists(DATA_DIR):
        print(f"❌ No existe la carpeta de datos: {DATA_DIR}")
        return

    archivos_dat = [
        os.path.join(DATA_DIR, f)
        for f in os.listdir(DATA_DIR)
        if f.lower().endswith('.dat')
    ]

    if not archivos_dat:
        print(f"❌ No se encontraron archivos .dat en: {DATA_DIR}")
        return

    print(f"📂 {len(archivos_dat)} archivo(s) .dat encontrado(s)\n")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    total = 0

    for ruta in sorted(archivos_dat):
        nombre = os.path.basename(ruta)
        n = procesar_dat(ruta, cursor)
        total += n
        print(f"  ✅ {nombre}: {n} registros actualizados")

    conn.commit()
    conn.close()
    print(f"\n🎉 Listo. Total registros corregidos: {total}")


if __name__ == "__main__":
    main()
