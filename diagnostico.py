#!/usr/bin/env python3
"""
Script de diagnóstico para verificar valores en la base de datos
"""
import sqlite3
import os

DB_PATH = "database/bolsa_datos.db"

def format_spanish(value, decimals=2):
    """Formatea número con separadores de miles (punto) y decimal (coma)"""
    try:
        if value is None:
            return "0,00"
        
        num = float(value)
        
        # Formatear con separador de miles inglés
        formatted = f"{num:,.{decimals}f}"
        
        # Convertir a formato español
        parts = formatted.split('.')
        if len(parts) == 2:
            integer_part = parts[0].replace(',', '.')
            decimal_part = parts[1]
            result = f"{integer_part},{decimal_part}"
        else:
            result = formatted.replace(',', '.')
        
        return result
    except:
        return str(value)

def diagnosticar_bd():
    """Diagnostica el contenido de la base de datos"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ No se encuentra la base de datos en: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO DE BASE DE DATOS - BVCLOCAL")
    print("="*80)
    
    # 1. Información general
    cursor.execute("SELECT COUNT(*) FROM mercado")
    total = cursor.fetchone()[0]
    print(f"\n1️⃣ INFORMACIÓN GENERAL:")
    print(f"   Total de registros: {total:,}")
    
    # 2. Fechas disponibles
    cursor.execute("SELECT DISTINCT fecha FROM mercado ORDER BY fecha DESC LIMIT 5")
    fechas = cursor.fetchall()
    print(f"\n2️⃣ ÚLTIMAS 5 FECHAS:")
    for fecha, in fechas:
        cursor.execute("SELECT COUNT(*) FROM mercado WHERE fecha = ?", (fecha,))
        count = cursor.fetchone()[0]
        print(f"   • {fecha}: {count} acciones")
    
    if not fechas:
        print("   ⚠️ No hay datos en la base de datos")
        conn.close()
        return
    
    ultima_fecha = fechas[0][0]
    
    # 3. Top 10 más negociadas
    print(f"\n3️⃣ TOP 10 MÁS NEGOCIADAS ({ultima_fecha}):")
    print(f"{'#':<3} {'Símbolo':<8} {'Nombre':<25} {'Cierre':>12} {'Volumen RAW':>18} {'Volumen Formateado':<20}")
    print("-" * 100)
    
    cursor.execute("""
        SELECT simbolo, nombre, cierre, volumen, variacion
        FROM mercado
        WHERE fecha = ?
        ORDER BY volumen DESC
        LIMIT 10
    """, (ultima_fecha,))
    
    resultados = cursor.fetchall()
    
    valores_esperados = {
        'PGR': 11548986.72,
        'RST': 8292782.82,
        'TPG': 1173175.69,
        'TDV.D': 5778605.5,
        'BPV': 3582507.69
    }
    
    for i, (simbolo, nombre, cierre, volumen, variacion) in enumerate(resultados, 1):
        nombre_corto = nombre[:22] + "..." if len(nombre) > 25 else nombre
        vol_formatted = format_spanish(volumen, 2)
        
        # Verificar si el valor es correcto
        estado = ""
        if simbolo in valores_esperados:
            esperado = valores_esperados[simbolo]
            diferencia_ratio = abs(volumen - esperado) / esperado if esperado > 0 else 1
            
            if diferencia_ratio < 0.01:  # Menos de 1% de diferencia
                estado = "✅"
            elif volumen < esperado * 0.01:  # Valor 100x menor
                estado = "❌ 100x menor"
            elif volumen < esperado * 0.1:  # Valor 10x menor
                estado = "⚠️ 10x menor"
            elif volumen > esperado * 10:  # Valor 10x mayor
                estado = "⚠️ 10x mayor"
            else:
                estado = "⚠️"
        
        print(f"{i:<3} {simbolo:<8} {nombre_corto:<25} {cierre:>12.2f} {volumen:>18.2f} {vol_formatted:<20} {estado}")
    
    # 4. Verificación específica de TPG
    print(f"\n4️⃣ VERIFICACIÓN DETALLADA DE TPG:")
    cursor.execute("""
        SELECT fecha, apertura, cierre, volumen, variacion
        FROM mercado
        WHERE simbolo = 'TPG'
        ORDER BY fecha DESC
        LIMIT 5
    """, )
    
    tpg_datos = cursor.fetchall()
    
    if tpg_datos:
        print(f"{'Fecha':<12} {'Apertura':>10} {'Cierre':>10} {'Volumen RAW':>18} {'Volumen Formateado':<20} {'Estado':<15}")
        print("-" * 100)
        
        for fecha, apertura, cierre, volumen, variacion in tpg_datos:
            vol_formatted = format_spanish(volumen, 2)
            
            # Verificar contra valor esperado
            if 1000000 <= volumen <= 1500000:
                estado = "✅ Correcto"
            elif volumen < 10000:
                estado = "❌ 100x menor"
            elif volumen > 10000000:
                estado = "❌ 1000x mayor"
            else:
                estado = "⚠️ Verificar"
            
            print(f"{fecha:<12} {apertura:>10.2f} {cierre:>10.2f} {volumen:>18.2f} {vol_formatted:<20} {estado:<15}")
    else:
        print("   ⚠️ No hay datos de TPG")
    
    # 5. Estadísticas de rangos de volumen
    print(f"\n5️⃣ DISTRIBUCIÓN DE VOLÚMENES:")
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN volumen < 1000 THEN 1 END) as muy_bajo,
            COUNT(CASE WHEN volumen BETWEEN 1000 AND 100000 THEN 1 END) as bajo,
            COUNT(CASE WHEN volumen BETWEEN 100000 AND 1000000 THEN 1 END) as medio,
            COUNT(CASE WHEN volumen BETWEEN 1000000 AND 10000000 THEN 1 END) as alto,
            COUNT(CASE WHEN volumen > 10000000 THEN 1 END) as muy_alto
        FROM mercado
        WHERE fecha = ?
    """, (ultima_fecha,))
    
    muy_bajo, bajo, medio, alto, muy_alto = cursor.fetchone()
    
    print(f"   • < 1K:        {muy_bajo:>4} acciones")
    print(f"   • 1K - 100K:   {bajo:>4} acciones")
    print(f"   • 100K - 1M:   {medio:>4} acciones")
    print(f"   • 1M - 10M:    {alto:>4} acciones ← Rango esperado")
    print(f"   • > 10M:       {muy_alto:>4} acciones")
    
    if muy_alto > 0:
        print(f"\n   ⚠️ HAY {muy_alto} ACCIONES CON VOLUMEN > 10M (posible error de extracción)")
    
    # 6. Recomendaciones
    print(f"\n6️⃣ RECOMENDACIONES:")
    
    cursor.execute("""
        SELECT COUNT(*) FROM mercado 
        WHERE fecha = ? AND volumen > 10000000
    """, (ultima_fecha,))
    
    problemas = cursor.fetchone()[0]
    
    if problemas > 0:
        print(f"   ❌ PROBLEMA DETECTADO: {problemas} acciones tienen volumen > 10M")
        print(f"   📝 SOLUCIÓN:")
        print(f"      1. Verifica la columna correcta en el archivo .dat")
        print(f"      2. Asegúrate de que estás dividiendo por 1000 si es necesario")
        print(f"      3. Ejecuta: python procesar_todo.py para reprocesar")
    else:
        cursor.execute("""
            SELECT COUNT(*) FROM mercado 
            WHERE fecha = ? AND volumen BETWEEN 1000000 AND 10000000
        """, (ultima_fecha,))
        
        correctos = cursor.fetchone()[0]
        
        if correctos > 0:
            print(f"   ✅ {correctos} acciones tienen volumen en rango esperado (1M - 10M)")
            print(f"   ✅ Los datos parecen estar correctos")
        else:
            print(f"   ⚠️ NO hay acciones con volumen > 1M")
            print(f"   📝 Posible problema:")
            print(f"      - Puede que NO estés leyendo la columna correcta")
            print(f"      - O puede que los datos estén divididos de más")
    
    conn.close()
    
    print("\n" + "="*80)
    print("✅ Diagnóstico completado")
    print("="*80 + "\n")

if __name__ == "__main__":
    diagnosticar_bd()
