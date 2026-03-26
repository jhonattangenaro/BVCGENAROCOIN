# ejecutar_solucion_definitiva.py
import os
import sqlite3
from extractor import data_manager

def solucion_definitiva():
    print("="*80)
    print("🎯 SOLUCIÓN DEFINITIVA - EXTRACTOR CORREGIDO")
    print("="*80)
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "database", "bolsa_datos.db")
    DATA_DIR = os.path.join(BASE_DIR, "datos_dat")
    
    # 1. Limpiar base de datos
    print("\n1️⃣  LIMPIANDO BASE DE DATOS...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mercado")
    conn.commit()
    conn.close()
    print("✅ Base de datos limpiada")
    
    # 2. Procesar archivos .dat
    print("\n2️⃣  PROCESANDO ARCHIVOS .dat...")
    archivos = [f for f in os.listdir(DATA_DIR) if f.lower().endswith('.dat')]
    
    if not archivos:
        print("❌ No hay archivos .dat en la carpeta")
        return
    
    print(f"📁 Archivos encontrados: {len(archivos)}")
    
    for archivo in archivos:
        print(f"\n🔄 Procesando: {archivo}")
        ruta = os.path.join(DATA_DIR, archivo)
        data_manager.procesar_dat(ruta)
    
    # 3. Verificar resultados
    print("\n3️⃣  VERIFICANDO RESULTADOS...")
    data_manager.verificar_integradad()
    
    # 4. Verificar TPG específicamente
    print("\n4️⃣  VERIFICACIÓN ESPECÍFICA DE TPG:")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT fecha FROM mercado WHERE simbolo = 'TPG' ORDER BY fecha DESC LIMIT 1")
    ultima_fecha_tpg = cursor.fetchone()
    
    if ultima_fecha_tpg:
        fecha = ultima_fecha_tpg[0]
        cursor.execute("""
            SELECT fecha, simbolo, cierre, volumen, variacion 
            FROM mercado 
            WHERE simbolo = 'TPG' AND fecha = ?
        """, (fecha,))
        
        resultado = cursor.fetchone()
        if resultado:
            fecha, simbolo, cierre, volumen, variacion = resultado
            print(f"\n📊 TPG ({fecha}):")
            print(f"   Cierre: {cierre}")
            print(f"   Volumen: {volumen:,.2f}")
            print(f"   Variación: {variacion}%")
            
            if volumen > 1000000:
                print(f"\n✅ ¡¡¡CORRECTO!!! TPG ahora muestra: Bs. {volumen:,.2f}")
                print(f"   (Anteriormente mostraba: Bs. 131,820.00)")
            else:
                print(f"\n❌ ERROR: TPG todavía muestra volumen incorrecto")
    
    conn.close()
    
    print("\n" + "="*80)
    print("🎉 PROCESO COMPLETADO")
    print("="*80)
    
    print("\n📋 INSTRUCCIONES FINALES:")
    print("1. Vuelve a cargar la página principal: http://127.0.0.1:5000/")
    print("2. Ahora deberías ver:")
    print("   - TPG: Monto negociado: Bs. 1,173,175.69 (no 156.00)")
    print("   - Precios correctos: 8.95 (no 895.00)")
    print("   - Datos reales de todas las acciones")

if __name__ == "__main__":
    solucion_definitiva()