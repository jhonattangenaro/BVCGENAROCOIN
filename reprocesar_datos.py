import sqlite3
import os

def limpiar_y_reprocesar():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "database", "bolsa_datos.db")
    DATA_DIR = os.path.join(BASE_DIR, "datos_dat")
    
    # 1. Vaciar la tabla mercado
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mercado")
    print(f"🗑️  Tabla vaciada: {cursor.rowcount} registros eliminados")
    conn.commit()
    conn.close()
    
    # 2. Importar el extractor corregido
    from extractor import data_manager
    
    # 3. Reprocesar todos los archivos
    if not os.path.exists(DATA_DIR):
        print(f"❌ No existe carpeta: {DATA_DIR}")
        return
    
    archivos = [f for f in os.listdir(DATA_DIR) if f.endswith('.dat')]
    print(f"📁 Encontrados {len(archivos)} archivos .dat")
    
    for archivo in archivos:
        print(f"\n🔄 Procesando: {archivo}")
        ruta_completa = os.path.join(DATA_DIR, archivo)
        if data_manager.procesar_dat(ruta_completa):
            print(f"   ✅ Correcto")
        else:
            print(f"   ❌ Falló")
    
    # 4. Verificar resultados
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Total registros
    cursor.execute("SELECT COUNT(*) FROM mercado")
    total = cursor.fetchone()[0]
    print(f"\n📊 Total registros en BD: {total}")
    
    # Ver TPG
    cursor.execute("SELECT fecha, simbolo, volumen FROM mercado WHERE simbolo = 'TPG' ORDER BY fecha DESC LIMIT 3")
    tpg_data = cursor.fetchall()
    
    print(f"\n🔍 Datos de TPG:")
    for fecha, simbolo, volumen in tpg_data:
        print(f"   {fecha} | {simbolo} | Volumen: {volumen:,.2f}")
    
    # Top negociadas última fecha
    cursor.execute("SELECT MAX(fecha) FROM mercado")
    ultima_fecha = cursor.fetchone()[0]
    
    if ultima_fecha:
        print(f"\n🏆 Top 5 más negociadas ({ultima_fecha}):")
        cursor.execute("""
            SELECT simbolo, nombre, volumen 
            FROM mercado 
            WHERE fecha = ? AND volumen > 0 
            ORDER BY volumen DESC 
            LIMIT 5
        """, (ultima_fecha,))
        
        for simbolo, nombre, volumen in cursor.fetchall():
            print(f"   {simbolo:6} | {nombre[:20]:20} | Bs. {volumen:>15,.2f}")
    
    conn.close()
    print("\n✅ Proceso completado")

if __name__ == "__main__":
    limpiar_y_reprocesar()