import sqlite3
import os
import re
from datetime import datetime

class DataManager:
    def __init__(self, db_path="database/bolsa_datos.db"):
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
        self._crear_tablas()

    def _crear_tablas(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla para acciones individuales
        cursor.execute('''CREATE TABLE IF NOT EXISTS mercado (
            fecha TEXT, 
            simbolo TEXT, 
            nombre TEXT, 
            apertura REAL, 
            maximo REAL, 
            minimo REAL, 
            cierre REAL, 
            volumen REAL,
            variacion REAL,
            PRIMARY KEY (fecha, simbolo)
        )''')

        # Tabla para Índices Globales (IBC y BCV)
        cursor.execute('''CREATE TABLE IF NOT EXISTS indicadores (
            fecha TEXT PRIMARY KEY,
            dolar REAL DEFAULT 0,
            ibc REAL DEFAULT 0
        )''')
        
        conn.commit()
        conn.close()
        print("✅ Base de datos y tablas de indicadores listas.")

    def procesar_dat(self, ruta_archivo):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            nombre_archivo = os.path.basename(ruta_archivo)
            
            # Extraer fecha del nombre: soporta YYYYMMDD y DDMMYYYY
            match = re.search(r'(\d{8})', nombre_archivo)
            if match:
                f = match.group(1)
                fecha = f"{f[:4]}-{f[4:6]}-{f[6:]}" if int(f[:4]) > 1900 else f"{f[4:]}-{f[2:4]}-{f[:2]}"
            else:
                fecha = datetime.now().strftime('%Y-%m-%d')

            with open(ruta_archivo, 'r', encoding='latin-1') as fh:
                lineas = fh.readlines()
                
                # -------------------------------------------------------
                # CAPTURA DEL IBC: línea que empieza con IG|
                # Formato: IG|DDMMYYYY|valor_ibc|var_abs|var_pct|...
                # -------------------------------------------------------
                valor_ibc = 0.0
                ibc_var   = 0.0
                ibc_var_pct = 0.0
                
                for linea in lineas[:5]:
                    if linea.startswith('IG|'):
                        partes = linea.strip().split('|')
                        if len(partes) >= 3: valor_ibc   = self._convertir(partes[2])
                        if len(partes) >= 4: ibc_var     = self._convertir(partes[3])
                        if len(partes) >= 5: ibc_var_pct = self._convertir(partes[4])
                        print(f"📈 IBC (línea IG): {valor_ibc} | Var: {ibc_var} ({ibc_var_pct}%) → {fecha}")
                        break
                
                if valor_ibc > 0:
                    cursor.execute('''
                        INSERT INTO indicadores (fecha, ibc, ibc_var, ibc_var_pct)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(fecha) DO UPDATE SET
                            ibc=excluded.ibc,
                            ibc_var=excluded.ibc_var,
                            ibc_var_pct=excluded.ibc_var_pct
                    ''', (fecha, valor_ibc, ibc_var, ibc_var_pct))
                
                # -------------------------------------------------------
                # PROCESAMIENTO DE ACCIONES (líneas R|...)
                # Formato: R|NOMBRE|SIMBOLO|APERTURA|CIERRE|VAR_ABS|VAR_PCT|MIN|MAX|PROM|OPS|TITULOS|EFECTIVO||IND|
                # -------------------------------------------------------
                registros = 0
                for linea in lineas:
                    if not linea.startswith('R|'):
                        continue
                    partes = linea.strip().split('|')
                    if len(partes) < 8: continue
                    try:
                        nombre   = partes[1].strip()
                        simbolo  = partes[2].strip()
                        apertura = self._convertir(partes[3])
                        cierre   = self._convertir(partes[4])
                        var_pct  = self._convertir(partes[6])
                        minimo   = self._convertir(partes[7])
                        maximo   = self._convertir(partes[8]) if len(partes) > 8 else 0.0
                        volumen  = self._convertir(partes[12]) if len(partes) > 12 else 0.0

                        cursor.execute('''
                            INSERT OR REPLACE INTO mercado
                            (fecha, simbolo, nombre, apertura, maximo, minimo, cierre, volumen, variacion)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (fecha, simbolo, nombre, apertura, maximo, minimo, cierre, volumen, var_pct))
                        registros += 1
                    except Exception as ex:
                        print(f"  ⚠️ Error en línea: {ex}")
                        continue

            conn.commit()
            print(f"📊 {nombre_archivo}: {registros} acciones procesadas.")
            return True
            
        except Exception as e:
            print(f"❌ Error procesando {ruta_archivo}: {e}")
            return False
        finally:
            conn.close()
    
    def _convertir(self, valor, es_variacion=False):
        """Convierte string numérico europeo (1.234,56) a float (1234.56)"""
        if not valor: return 0.0
        val = str(valor).strip().replace(' ', '').replace('%', '')
        
        try:
            # Si tiene punto y coma, es formato 1.234,56
            if ',' in val and '.' in val:
                val = val.replace('.', '').replace(',', '.')
            # Si solo tiene coma, es 1234,56
            elif ',' in val:
                val = val.replace(',', '.')
                
            return float(val)
        except:
            return 0.0

# Instancia única para el proyecto
data_manager = DataManager()