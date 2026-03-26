# analizar_archivo.py
import os

def analizar_archivo_dat():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "datos_dat")
    
    # Buscar archivos .dat
    archivos = [f for f in os.listdir(DATA_DIR) if f.lower().endswith('.dat')]
    
    if not archivos:
        print("❌ No hay archivos .dat")
        return
    
    print(f"📁 Archivos encontrados: {len(archivos)}")
    
    for archivo in archivos:
        ruta = os.path.join(DATA_DIR, archivo)
        print(f"\n🔍 Analizando: {archivo}")
        print("="*80)
        
        with open(ruta, 'r', encoding='utf-8', errors='ignore') as f:
            lineas = f.readlines()
            
            # Buscar TPG
            for i, linea in enumerate(lineas, 1):
                linea = linea.strip()
                
                if 'TPG' in linea and linea.startswith('R|'):
                    print(f"\n✅ LÍNEA TPG ENCONTRADA (línea {i}):")
                    print(f"   {linea}")
                    
                    # Analizar columnas
                    partes = linea.split('|')
                    print(f"\n📊 ANÁLISIS DE COLUMNAS ({len(partes)} columnas):")
                    print("-"*80)
                    
                    for idx, parte in enumerate(partes):
                        parte_limpia = parte.strip()
                        print(f"   Columna {idx:2d}: '{parte_limpia}'")
                    
                    # Mostrar columnas sospechosas de ser "efectivo"
                    print(f"\n🔍 COLUMNAS QUE PODRÍAN SER EFECTIVO:")
                    print("-"*80)
                    
                    # Buscar columnas que contengan números grandes
                    for idx, parte in enumerate(partes):
                        parte_limpia = parte.strip()
                        if parte_limpia and parte_limpia.replace(',', '').replace('.', '').isdigit():
                            try:
                                num = float(parte_limpia.replace(',', '.'))
                                if num > 100000:  # Números grandes (posible efectivo)
                                    print(f"   [{idx:2d}] '{parte_limpia}' → {num:,.2f} ← ¡POSIBLE EFECTIVO!")
                                elif num > 1000:  # Números medianos
                                    print(f"   [{idx:2d}] '{parte_limpia}' → {num:,.2f}")
                            except:
                                pass
                    
                    # Mostrar estructura típica esperada
                    print(f"\n📋 ESTRUCTURA ESPERADA vs REAL:")
                    print("-"*80)
                    print("ESPERADO:")
                    print("   [0] 'R' (tipo)")
                    print("   [1] 'T. PALO GRANDE' (nombre)")
                    print("   [2] 'TPG' (símbolo)")
                    print("   [3] '8.85' (apertura)")
                    print("   [4] '8.95' (cierre)")
                    print("   [5] '1.1' (??)")
                    print("   [6] '13.18' (variación %)")
                    print("   [7] '21.9' (mínimo)")
                    print("   [8] '5.8' (máximo)")
                    print("   [9] '9.156' (??)")
                    print("   [10] '131820' (volumen unidades)")
                    print("   [11] '1173175.69' (EFECTIVO Bs.) ← ESTA BUSCAMOS")
                    print("   [12] '1' (operaciones)")
                    
                    print(f"\nREAL:")
                    for idx, parte in enumerate(partes):
                        if idx < len(partes):
                            print(f"   [{idx:2d}] '{partes[idx].strip()}'")
                    
                    # Hacer prueba de extracción
                    print(f"\n🧪 PRUEBA DE EXTRACCIÓN:")
                    print("-"*80)
                    
                    if len(partes) >= 12:
                        print(f"   Probando columna 10: '{partes[10].strip()}'")
                        print(f"   Probando columna 11: '{partes[11].strip()}'")
                        print(f"   Probando columna 12: '{partes[12].strip() if len(partes) > 12 else 'NO EXISTE'}'")
                        print(f"   Probando columna 13: '{partes[13].strip() if len(partes) > 13 else 'NO EXISTE'}'")
                    
                    break  # Solo analizar primera aparición de TPG
            
            print(f"\n📄 Total líneas en archivo: {len(lineas)}")
            print("="*80)

if __name__ == "__main__":
    analizar_archivo_dat()