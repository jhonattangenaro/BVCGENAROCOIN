#!/usr/bin/env python3
"""
Script simple para corregir templates/index.html eliminando la línea problemática
"""
import shutil
from pathlib import Path

def corregir_index():
    """Corrige el archivo index.html eliminando líneas problemáticas"""
    
    templates_dir = Path.cwd() / "templates"
    index_path = templates_dir / "index.html"
    
    if not index_path.exists():
        print(f"❌ No se encuentra: {index_path}")
        return False
    
    print(f"📄 Archivo encontrado: {index_path}")
    
    # Hacer backup
    backup_path = index_path.with_suffix('.html.backup')
    shutil.copy(index_path, backup_path)
    print(f"📦 Backup creado: {backup_path}")
    
    # Leer archivo
    with open(index_path, 'r', encoding='utf-8') as f:
        lineas = f.readlines()
    
    print(f"📊 Total de líneas: {len(lineas)}")
    
    # Buscar y eliminar líneas problemáticas
    lineas_nuevas = []
    lineas_eliminadas = []
    
    for i, linea in enumerate(lineas, 1):
        # Buscar la línea problemática
        if 'Valor: {{ acc.volumen }}' in linea and '<p' in linea:
            lineas_eliminadas.append((i, linea.strip()))
            print(f"   🗑️  Línea {i} eliminada: {linea.strip()[:60]}...")
        else:
            lineas_nuevas.append(linea)
    
    if lineas_eliminadas:
        # Guardar archivo corregido
        with open(index_path, 'w', encoding='utf-8') as f:
            f.writelines(lineas_nuevas)
        
        print(f"\n✅ Archivo corregido:")
        print(f"   • Líneas eliminadas: {len(lineas_eliminadas)}")
        print(f"   • Líneas finales: {len(lineas_nuevas)}")
        
        print(f"\n🚀 SIGUIENTE PASO:")
        print(f"   1. Detén Flask (Ctrl+C)")
        print(f"   2. Ejecuta: python app.py")
        print(f"   3. Recarga la página (Ctrl+Shift+R)")
        
        return True
    else:
        print(f"\n⚠️  No se encontraron líneas problemáticas")
        print(f"   El archivo puede ya estar corregido")
        
        # Verificar si tiene la versión correcta
        contenido = ''.join(lineas)
        if 'format_spanish(acc.volumen, 2)' in contenido:
            print(f"   ✅ Detectado uso de format_spanish - archivo parece correcto")
        
        return False

if __name__ == "__main__":
    print("\n" + "="*80)
    print("🔧 CORRECCIÓN AUTOMÁTICA DE templates/index.html")
    print("="*80 + "\n")
    
    if corregir_index():
        print("\n" + "="*80)
        print("✅ CORRECCIÓN COMPLETADA")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("⚠️  VERIFICACIÓN MANUAL REQUERIDA")
        print("="*80)
        print("\nAbre templates/index.html y busca estas líneas:")
        print("❌ <p class=\"text-[10px] text-slate-500\">Valor: {{ acc.volumen }}</p>")
        print("\nSi las encuentras, elimínalas manualmente.")
