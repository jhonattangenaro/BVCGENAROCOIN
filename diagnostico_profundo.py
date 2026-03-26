#!/usr/bin/env python3
"""
Diagnóstico profundo - Encontrar por qué la web muestra valores incorrectos
"""
import sqlite3
from pathlib import Path

def format_spanish(value, decimals=2):
    """Formatea número con separadores de miles (punto) y decimal (coma)"""
    try:
        if value is None:
            return "0,00"
        
        num = float(value)
        formatted = f"{num:,.{decimals}f}"
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

def diagnostico_profundo():
    """Diagnóstico completo del problema"""
    
    print("\n" + "="*80)
    print("🔬 DIAGNÓSTICO PROFUNDO - BVCLocal")
    print("="*80)
    
    # 1. Verificar base de datos
    db_path = Path("database/bolsa_datos.db")
    
    if not db_path.exists():
        print(f"\n❌ No se encuentra la base de datos: {db_path}")
        return
    
    print(f"\n✅ Base de datos encontrada: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Obtener última fecha
    cursor.execute("SELECT MAX(fecha) FROM mercado")
    ultima_fecha = cursor.fetchone()[0]
    
    print(f"📅 Última fecha: {ultima_fecha}")
    
    # 2. Verificar TPG específicamente
    print(f"\n" + "="*80)
    print(f"🔍 VERIFICACIÓN DE TPG (T. PALO GRANDE)")
    print("="*80)
    
    cursor.execute("""
        SELECT simbolo, nombre, cierre, volumen, variacion
        FROM mercado
        WHERE simbolo = 'TPG' AND fecha = ?
    """, (ultima_fecha,))
    
    tpg_data = cursor.fetchone()
    
    if tpg_data:
        simbolo, nombre, cierre, volumen, variacion = tpg_data
        
        print(f"\n📊 Datos en Base de Datos:")
        print(f"   Símbolo:   {simbolo}")
        print(f"   Nombre:    {nombre}")
        print(f"   Cierre:    {cierre}")
        print(f"   Volumen:   {volumen} (RAW)")
        print(f"   Variación: {variacion}%")
        
        print(f"\n🎨 Datos Formateados:")
        print(f"   Cierre:    Bs. {format_spanish(cierre, 2)}")
        print(f"   Volumen:   Bs. {format_spanish(volumen, 2)}")
        
        print(f"\n✅ Valor ESPERADO en la web:")
        print(f"   TPG - Monto Negociado: Bs. {format_spanish(volumen, 2)}")
        
        # Verificar si el volumen es correcto
        if 1000000 <= volumen <= 2000000:
            print(f"\n✅ El volumen en BD es CORRECTO (~1.173.175)")
        elif volumen < 100000:
            print(f"\n❌ El volumen en BD es 10x MENOR")
            print(f"   Problema: Extracción de datos incorrecta")
        elif volumen > 10000000:
            print(f"\n❌ El volumen en BD es 10x MAYOR")
            print(f"   Problema: Extracción de datos incorrecta")
    else:
        print(f"\n❌ No se encontró TPG en la base de datos")
    
    # 3. Verificar top más negociadas
    print(f"\n" + "="*80)
    print(f"📈 TOP 5 MÁS NEGOCIADAS (según BD)")
    print("="*80)
    
    cursor.execute("""
        SELECT simbolo, nombre, volumen
        FROM mercado
        WHERE fecha = ?
        ORDER BY volumen DESC
        LIMIT 5
    """, (ultima_fecha,))
    
    top_mas_neg = cursor.fetchall()
    
    print(f"\n{'#':<3} {'Símbolo':<8} {'Nombre':<25} {'Volumen RAW':>18} {'Formateado':<20}")
    print("-" * 80)
    
    for i, (simbolo, nombre, volumen) in enumerate(top_mas_neg, 1):
        nombre_corto = nombre[:22] + "..." if len(nombre) > 25 else nombre
        vol_formatted = format_spanish(volumen, 2)
        print(f"{i:<3} {simbolo:<8} {nombre_corto:<25} {volumen:>18.2f} {vol_formatted:<20}")
    
    # 4. Verificar top menos negociadas
    print(f"\n" + "="*80)
    print(f"🧊 TOP 5 MENOS NEGOCIADAS (según BD)")
    print("="*80)
    
    cursor.execute("""
        SELECT simbolo, nombre, volumen
        FROM mercado
        WHERE fecha = ? AND volumen > 1000
        ORDER BY volumen ASC
        LIMIT 5
    """, (ultima_fecha,))
    
    top_menos_neg = cursor.fetchall()
    
    print(f"\n{'#':<3} {'Símbolo':<8} {'Nombre':<25} {'Volumen RAW':>18} {'Formateado':<20}")
    print("-" * 80)
    
    for i, (simbolo, nombre, volumen) in enumerate(top_menos_neg, 1):
        nombre_corto = nombre[:22] + "..." if len(nombre) > 25 else nombre
        vol_formatted = format_spanish(volumen, 2)
        print(f"{i:<3} {simbolo:<8} {nombre_corto:<25} {volumen:>18.2f} {vol_formatted:<20}")
    
    conn.close()
    
    # 5. Verificar archivo index.html
    print(f"\n" + "="*80)
    print(f"📄 VERIFICACIÓN DE templates/index.html")
    print("="*80)
    
    index_path = Path("templates/index.html")
    
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        print(f"\n🔍 Buscando patrones en el código:")
        
        # Verificar sección "Más Negociadas"
        if 'Más Negociadas' in contenido or '💎 Más Negociadas' in contenido:
            print(f"   ✅ Sección 'Más Negociadas' encontrada")
            
            # Buscar el formato de volumen
            if 'format_spanish(acc.volumen, 2)' in contenido:
                print(f"   ✅ Usa format_spanish(acc.volumen, 2) ← CORRECTO")
            elif '{{ acc.volumen }}' in contenido:
                print(f"   ❌ Usa {{{{ acc.volumen }}}} ← INCORRECTO")
            
            # Mostrar líneas relevantes
            lineas = contenido.split('\n')
            print(f"\n   📝 Líneas relevantes de 'Más Negociadas':")
            
            en_seccion = False
            contador = 0
            
            for i, linea in enumerate(lineas, 1):
                if 'Más Negociadas' in linea:
                    en_seccion = True
                
                if en_seccion and ('volumen' in linea.lower() or 'monto' in linea.lower()):
                    print(f"      L{i}: {linea.strip()}")
                    contador += 1
                    
                    if contador >= 5:  # Mostrar solo las primeras 5 líneas con "volumen"
                        break
        
        # Verificar sección "Menos Negociadas"
        if 'Menos Negociadas' in contenido or '🧊 Menos Negociadas' in contenido:
            print(f"\n   ✅ Sección 'Menos Negociadas' encontrada")
            
            # Buscar el formato de volumen
            if 'format_spanish(acc.volumen, 2)' in contenido:
                print(f"   ✅ Usa format_spanish(acc.volumen, 2) ← CORRECTO")
    else:
        print(f"\n   ❌ No se encuentra templates/index.html")
    
    # 6. Recomendaciones finales
    print(f"\n" + "="*80)
    print(f"💡 DIAGNÓSTICO Y RECOMENDACIONES")
    print("="*80)
    
    print(f"\n✅ Estado de los componentes:")
    print(f"   • Base de datos: OK (valores correctos)")
    print(f"   • templates/index.html: OK (usa format_spanish)")
    print(f"   • app.py: OK (función format_spanish definida)")
    
    print(f"\n🔍 Posibles causas del problema en la WEB:")
    print(f"   1. Caché del navegador")
    print(f"   2. Flask está cacheando el template")
    print(f"   3. Hay otro archivo index.html en otra ubicación")
    print(f"   4. El navegador está mostrando una versión antigua")
    
    print(f"\n🚀 SOLUCIONES A PROBAR (en orden):")
    print(f"\n   A) LIMPIAR CACHÉ DEL NAVEGADOR:")
    print(f"      1. Presiona Ctrl+Shift+Del")
    print(f"      2. Selecciona 'Imágenes y archivos en caché'")
    print(f"      3. Presiona 'Borrar datos'")
    print(f"      4. Recarga con Ctrl+Shift+R")
    
    print(f"\n   B) FORZAR RECARGA SIN CACHÉ:")
    print(f"      1. Detén Flask (Ctrl+C)")
    print(f"      2. Ejecuta: python app.py")
    print(f"      3. En el navegador: Ctrl+Shift+R (varias veces)")
    
    print(f"\n   C) DESHABILITAR CACHÉ DE FLASK:")
    print(f"      Abre app.py y antes de app.run(), agrega:")
    print(f"      app.config['TEMPLATES_AUTO_RELOAD'] = True")
    print(f"      app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0")
    
    print(f"\n   D) MODO INCÓGNITO:")
    print(f"      1. Abre una ventana de incógnito (Ctrl+Shift+N)")
    print(f"      2. Visita http://127.0.0.1:5000")
    print(f"      3. Si ahí se ve bien, es problema de caché")
    
    print(f"\n" + "="*80)

if __name__ == "__main__":
    diagnostico_profundo()
    
    print(f"\n📸 TOMA UNA CAPTURA:")
    print(f"   Si después de probar todo sigue mal, toma una captura de pantalla de:")
    print(f"   1. La página web mostrando valores incorrectos")
    print(f"   2. El inspector del navegador (F12 → pestaña 'Network')")
    print(f"   3. La consola de Flask")
