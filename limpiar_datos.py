# fix_all_data.py
import sqlite3
import os
from extractor import data_manager

def limpiar_y_reprocesar():
    print("🔄 LIMPIANDO Y REPROCESANDO DATOS")
    print("="*60)
    
    # 1. Limpiar base de datos
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "database", "bolsa_datos.db")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Contar registros actuales
    cursor.execute("SELECT COUNT(*) FROM mercado")
    total_antes = cursor.fetchone()[0]
    print(f"📊 Registros antes: {total_antes:,}")
    
    # Eliminar todo
    cursor.execute("DELETE FROM mercado")
    conn.commit()
    conn.close()
    
    print(f"🗑️  Base de datos limpiada")
    
    # 2. Reprocesar archivos
    DATA_DIR = os.path.join(BASE_DIR, "datos_dat")
    archivos = [f for f in os.listdir(DATA_DIR) if f.lower().endswith('.dat')]
    
    print(f"\n📁 Archivos a procesar: {len(archivos)}")
    
    for archivo in archivos:
        print(f"\n🔄 Procesando: {archivo}")
        ruta = os.path.join(DATA_DIR, archivo)
        data_manager.procesar_dat(ruta)
    
    # 3. Verificar resultados
    print("\n" + "="*60)
    print("✅ VERIFICACIÓN FINAL")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total registros
    cursor.execute("SELECT COUNT(*) FROM mercado")
    total = cursor.fetchone()[0]
    print(f"📊 Total registros: {total:,}")
    
    # Última fecha
    cursor.execute("SELECT MAX(fecha) FROM mercado")
    ultima_fecha = cursor.fetchone()[0]
    print(f"📅 Última fecha: {ultima_fecha}")
    
    # Top 10 más negociadas
    print(f"\n🏆 TOP 10 MÁS NEGOCIADAS ({ultima_fecha}):")
    cursor.execute("""
        SELECT simbolo, nombre, cierre, volumen, variacion 
        FROM mercado 
        WHERE fecha = ? 
        ORDER BY volumen DESC 
        LIMIT 10
    """, (ultima_fecha,))
    
    resultados = cursor.fetchall()
    for i, (simbolo, nombre, cierre, volumen, variacion) in enumerate(resultados, 1):
        print(f"{i:2d}. {simbolo:6} | {nombre[:20]:20} | C: {cierre:8.2f} | V: {volumen:>15,.2f} | Δ: {variacion:6.2f}%")
    
    # Verificar TPG específicamente
    print(f"\n🔍 VERIFICACIÓN TPG:")
    cursor.execute("""
        SELECT fecha, cierre, volumen 
        FROM mercado 
        WHERE simbolo = 'TPG' 
        ORDER BY fecha DESC 
        LIMIT 3
    """)
    
    tpg_data = cursor.fetchall()
    for fecha, cierre, volumen in tpg_data:
        print(f"   {fecha} | Cierre: {cierre:8.2f} | Volumen: {volumen:>15,.2f}")
        
        # Verificar si es correcto
        if volumen > 1000000:
            print(f"      ✅ CORRECTO: Volumen real (~1,173,175.69)")
        else:
            print(f"      ❌ ERROR: Volumen incorrecto (debería ser ~1,173,175.69)")
    
    conn.close()
    
    print("\n" + "="*60)
    print("🎉 PROCESO COMPLETADO")
    print("="*60)

if __name__ == "__main__":
    limpiar_y_reprocesar()