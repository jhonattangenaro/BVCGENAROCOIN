#!/usr/bin/env python3
"""
Script para verificar y corregir la instalación de templates
"""
import os
import shutil
from pathlib import Path

def verificar_templates():
    """Verifica la ubicación de los templates de Flask"""
    
    print("\n" + "="*80)
    print("🔍 VERIFICANDO UBICACIÓN DE TEMPLATES")
    print("="*80)
    
    # Directorio actual
    current_dir = Path.cwd()
    print(f"\n📁 Directorio actual: {current_dir}")
    
    # Buscar carpeta templates
    templates_dir = current_dir / "templates"
    
    if not templates_dir.exists():
        print(f"\n❌ No se encuentra la carpeta 'templates' en {current_dir}")
        print("   Creando carpeta 'templates'...")
        templates_dir.mkdir(exist_ok=True)
        print("   ✅ Carpeta creada")
    else:
        print(f"\n✅ Carpeta 'templates' encontrada: {templates_dir}")
    
    # Verificar archivos en templates
    print(f"\n📄 Archivos en templates/:")
    archivos_html = list(templates_dir.glob("*.html"))
    
    if archivos_html:
        for archivo in archivos_html:
            size = archivo.stat().st_size  # CORRECCIÓN: usar .stat().st_size
            print(f"   - {archivo.name} ({size:,} bytes)")
    else:
        print("   ⚠️ No hay archivos HTML en templates/")
    
    # Buscar index.html en el directorio actual
    index_actual = current_dir / "index.html"
    index_templates = templates_dir / "index.html"
    
    print(f"\n🔍 Buscando archivos index.html:")
    
    archivos_encontrados = []
    
    if index_actual.exists():
        size = index_actual.stat().st_size  # CORRECCIÓN
        print(f"   1. {index_actual} ({size:,} bytes)")
        archivos_encontrados.append(('actual', index_actual, size))
    
    if index_templates.exists():
        size = index_templates.stat().st_size  # CORRECCIÓN
        print(f"   2. {index_templates} ({size:,} bytes)")
        archivos_encontrados.append(('templates', index_templates, size))
    
    # Analizar contenido del archivo en templates (el que usa Flask)
    print(f"\n📊 ANÁLISIS DE CONTENIDO DE templates/index.html:")
    
    if index_templates.exists():
        with open(index_templates, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        # Buscar patrones problemáticos
        tiene_bug = False
        es_correcto = False
        
        # Patrón 1: Bug antiguo
        if 'Valor: {{ acc.volumen }}' in contenido or '<p class="text-[10px] text-slate-500">Valor: {{ acc.volumen }}</p>' in contenido:
            print(f"   ❌ VERSIÓN ANTIGUA DETECTADA (tiene el BUG)")
            print(f"      Encontrado: 'Valor: {{{{ acc.volumen }}}}'")
            tiene_bug = True
        
        # Patrón 2: Versión corregida
        if 'format_spanish(acc.volumen, 2)' in contenido and 'Monto Negociado' in contenido:
            print(f"   ✅ VERSIÓN CORREGIDA DETECTADA")
            print(f"      Encontrado: 'format_spanish(acc.volumen, 2)'")
            es_correcto = True
        
        if not tiene_bug and not es_correcto:
            print(f"   ⚠️ VERSIÓN DESCONOCIDA")
            print(f"      No se encontraron patrones conocidos")
        
        # Mostrar líneas específicas
        print(f"\n   📝 Buscando sección 'Más Negociadas'...")
        lineas = contenido.split('\n')
        for i, linea in enumerate(lineas, 1):
            if '💎 Más Negociadas' in linea or 'Más Negociadas' in linea:
                print(f"      Línea {i}: {linea.strip()[:60]}...")
                # Mostrar las siguientes 15 líneas
                for j in range(i, min(i+15, len(lineas))):
                    if 'volumen' in lineas[j].lower():
                        print(f"      Línea {j+1}: {lineas[j].strip()}")
                break
        
        return tiene_bug, es_correcto, index_templates
    else:
        print(f"   ❌ No existe templates/index.html")
        return False, False, None

def corregir_archivo(archivo_template):
    """Corrige el archivo templates/index.html"""
    print(f"\n🔧 CORRIGIENDO ARCHIVO: {archivo_template}")
    
    # Hacer backup
    backup_path = archivo_template.with_suffix('.html.backup')
    shutil.copy(archivo_template, backup_path)
    print(f"   📦 Backup creado: {backup_path}")
    
    # Leer contenido
    with open(archivo_template, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Aplicar correcciones
    correcciones = 0
    
    # Corrección 1: Sección "Más Negociadas"
    if '<p class="text-[10px] text-slate-500">Valor: {{ acc.volumen }}</p>' in contenido:
        print(f"   🔄 Corrigiendo sección 'Más Negociadas'...")
        
        # Reemplazar el bloque completo de "Más Negociadas"
        contenido = contenido.replace(
            '''                        <div class="text-right">
                            <p class="text-[10px] text-slate-400 uppercase font-bold">Monto</p>
                            <span class="font-bold text-sm">Bs. {{ format_spanish(acc.volumen, 2) }}</span>
                            <p class="text-[10px] text-slate-500">Valor: {{ acc.volumen }}</p>
                        </div>''',
            '''                        <div class="text-right">
                            <p class="text-[10px] text-slate-400 uppercase font-bold">Monto Negociado</p>
                            <span class="font-bold text-base text-blue-600">Bs. {{ format_spanish(acc.volumen, 2) }}</span>
                        </div>'''
        )
        correcciones += 1
    
    # Corrección 2: Sección "Menos Negociadas" (igual que Más Negociadas)
    if correcciones == 0:
        # Buscar y reemplazar manualmente cualquier referencia a acc.volumen sin format_spanish
        import re
        
        # Patrón: buscar <p>...</p> que contenga {{ acc.volumen }}
        patron = r'<p[^>]*>Valor:\s*{{\s*acc\.volumen\s*}}</p>'
        if re.search(patron, contenido):
            print(f"   🔄 Eliminando líneas 'Valor: {{{{ acc.volumen }}}}'...")
            contenido = re.sub(patron, '', contenido)
            correcciones += 1
    
    # Guardar cambios
    with open(archivo_template, 'w', encoding='utf-8') as f:
        f.write(contenido)
    
    print(f"   ✅ Archivo corregido ({correcciones} cambios aplicados)")
    return correcciones > 0

if __name__ == "__main__":
    tiene_bug, es_correcto, archivo_template = verificar_templates()
    
    print(f"\n" + "="*80)
    print("💡 RECOMENDACIONES:")
    print("="*80)
    
    if es_correcto and not tiene_bug:
        print("\n✅ El archivo templates/index.html está CORRECTO")
        print("\n🔍 Si aún ves valores incorrectos en la web:")
        print("   1. Detén Flask (Ctrl+C)")
        print("   2. Borra la caché: Remove-Item -Recurse -Force __pycache__")
        print("   3. Reinicia Flask: python app.py")
        print("   4. Recarga la página con Ctrl+Shift+R (forzar recarga)")
        
    elif tiene_bug:
        print("\n❌ El archivo templates/index.html tiene el BUG")
        print("\n🔧 OPCIONES:")
        print("   A) Corrección automática (recomendado)")
        print("   B) Corrección manual")
        
        respuesta = input("\n❓ ¿Deseas aplicar la corrección automática? (s/n): ")
        
        if respuesta.lower() in ['s', 'si', 'y', 'yes']:
            if corregir_archivo(archivo_template):
                print(f"\n✅ CORRECCIÓN APLICADA")
                print(f"\n🚀 PASOS SIGUIENTES:")
                print(f"   1. Detén Flask (Ctrl+C en la terminal donde corre)")
                print(f"   2. Ejecuta: python app.py")
                print(f"   3. Recarga la página en el navegador (Ctrl+Shift+R)")
                print(f"\n   Deberías ver los montos correctos ahora:")
                print(f"   • PGR: Bs. 11.548.986,72 ✅")
                print(f"   • TPG: Bs. 1.173.175,69 ✅")
        else:
            print(f"\n📝 Para corrección MANUAL:")
            print(f"   1. Abre: {archivo_template}")
            print(f"   2. Busca la línea: <p class=\"text-[10px] text-slate-500\">Valor: {{{{ acc.volumen }}}}</p>")
            print(f"   3. ELIMINA esa línea completa")
            print(f"   4. Guarda el archivo")
            print(f"   5. Reinicia Flask")
    else:
        print("\n⚠️ No se pudo determinar el estado del archivo")
        print("\n   Revisa manualmente templates/index.html")
    
    print(f"\n" + "="*80)