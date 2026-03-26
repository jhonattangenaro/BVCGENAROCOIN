# reprocesar_todo.py
import os
from extractor import data_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "datos_dat")

def reprocesar_todo():
    print("🚀 INICIANDO REPROCESAMIENTO COMPLETO")
    print("="*60)
    
    # Verificar carpeta de datos
    if not os.path.exists(DATA_DIR):
        print(f"❌ No existe la carpeta: {DATA_DIR}")
        os.makedirs(DATA_DIR, exist_ok=True)
        print(f"✅ Carpeta creada: {DATA_DIR}")
        print("   Coloca tus archivos .dat aquí y vuelve a ejecutar")
        return False
    
    archivos = [f for f in os.listdir(DATA_DIR) if f.lower().endswith('.dat')]
    
    if not archivos:
        print(f"⚠️ No se encontraron archivos .dat en: {DATA_DIR}")
        return False
    
    print(f"📁 Archivos encontrados: {len(archivos)}")
    
    # Buscar archivo que contenga TPG para análisis
    for archivo in archivos:
        ruta = os.path.join(DATA_DIR, archivo)
        with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
            contenido = f.read()
            if 'TPG' in contenido:
                print(f"\n🔍 Archivo con TPG encontrado: {archivo}")
                print(f"   Analizando estructura...")
                
                # Buscar línea de TPG
                for linea in contenido.split('\n'):
                    if 'TPG' in linea and linea.startswith('R|'):
                        print(f"\n   Línea TPG encontrada:")
                        print(f"   {linea[:100]}...")
                        partes = linea.strip().split('|')
                        print(f"   Número de columnas: {len(partes)}")
                        print(f"   Columna 11 (efectivo): '{partes[11] if len(partes) > 11 else 'NO EXISTE'}'")
                        break
                break
    
    print(f"\n🔄 Procesando {len(archivos)} archivos...")
    print("="*60)
    
    exitosos = 0
    for i, archivo in enumerate(sorted(archivos), 1):
        print(f"\n[{i}/{len(archivos)}] Procesando: {archivo}")
        ruta_completa = os.path.join(DATA_DIR, archivo)
        
        if data_manager.procesar_dat(ruta_completa):
            exitosos += 1
        else:
            print(f"   ❌ Error procesando {archivo}")
    
    print("\n" + "="*60)
    print(f"📊 RESUMEN FINAL:")
    print(f"   ✅ Archivos procesados exitosamente: {exitosos}/{len(archivos)}")
    
    # Verificar integridad
    if exitosos > 0:
        print(f"\n🔍 Verificando integridad de datos...")
        data_manager.verificar_integridad()
    
    return exitosos > 0

if __name__ == "__main__":
    reprocesar_todo()