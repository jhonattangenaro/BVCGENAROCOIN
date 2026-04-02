from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from extractor import data_manager
import sqlite3
import os
import csv
import re
from functools import wraps
from datetime import datetime, timedelta
import requests
import urllib3
import hashlib
try:
    import openpyxl
    OPENPYXL_DISPONIBLE = True
except ImportError:
    OPENPYXL_DISPONIBLE = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ========== CONFIGURACIÓN ==========
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_cambiar_en_produccion')
ADMIN_USER = "admin"
ADMIN_PASS = "12345"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "bolsa_datos.db")
DATA_DIR = os.path.join(BASE_DIR, "datos_dat")
FERIADOS_CSV = os.path.join(BASE_DIR, "feriados.csv")
DOLAR_XLSX = os.path.join(BASE_DIR, "dolar_bcv.xlsx")


def buscar_dat_reciente():
    if not os.path.exists(DATA_DIR):
        return None
    archivos = [(os.path.getmtime(os.path.join(DATA_DIR, f)), os.path.join(DATA_DIR, f))
                for f in os.listdir(DATA_DIR) if f.lower().endswith('.dat')]
    return max(archivos)[1] if archivos else None


def leer_ibc_de_dat(ruta_archivo):
    try:
        nombre = os.path.basename(ruta_archivo)
        match = re.search(r'(\d{8})', nombre)
        if match:
            f = match.group(1)
            fecha = f"{f[:4]}-{f[4:6]}-{f[6:]}" if int(f[:4]) > 1900 else f"{f[4:]}-{f[2:4]}-{f[:2]}"
        else:
            fecha = datetime.now().strftime('%Y-%m-%d')
        resultado = {'fecha': fecha, 'ibc': 0, 'ibc_var': 0, 'ibc_var_pct': 0, 'archivo': nombre}
        def conv(v):
            try:
                v = str(v).strip().replace('%','')
                if ',' in v and '.' in v: v = v.replace('.','').replace(',','.')
                elif ',' in v: v = v.replace(',','.')
                return float(v)
            except: return 0.0
        with open(ruta_archivo, 'r', encoding='latin-1') as fh:
            for linea in fh:
                if linea.startswith('IG|'):
                    partes = linea.strip().split('|')
                    if len(partes) >= 3: resultado['ibc'] = conv(partes[2])
                    if len(partes) >= 4: resultado['ibc_var'] = conv(partes[3])
                    if len(partes) >= 5: resultado['ibc_var_pct'] = conv(partes[4])
                    break
        return resultado
    except Exception as e:
        print(f"Error leyendo DAT: {e}")
        return None


def _fmt_fecha_xlsx(raw):
    f = str(int(raw))
    return f"{f[:4]}-{f[4:6]}-{f[6:]}" if len(f) == 8 else f


def leer_dolar_de_xlsx(fecha_str=None):
    if not OPENPYXL_DISPONIBLE or not os.path.exists(DOLAR_XLSX):
        return None
    try:
        wb  = openpyxl.load_workbook(DOLAR_XLSX, data_only=True)
        ws  = wb.active
        ultimo   = None
        objetivo = None
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0] or not row[1]: continue
            fecha_fmt = _fmt_fecha_xlsx(row[0])
            tasa      = float(row[1])
            var_pct   = round(float(row[2]) * 100, 4) if row[2] else 0.0
            ultimo    = {'fecha': fecha_fmt, 'tasa': tasa, 'variacion_pct': var_pct}
            if fecha_str and fecha_fmt == fecha_str:
                objetivo = dict(ultimo)
        wb.close()
        return objetivo if (fecha_str and objetivo) else ultimo
    except Exception as e:
        print(f"Error leyendo Excel dolar: {e}")
        return None


def leer_todos_dolar_xlsx():
    if not OPENPYXL_DISPONIBLE or not os.path.exists(DOLAR_XLSX):
        return {}
    try:
        wb  = openpyxl.load_workbook(DOLAR_XLSX, data_only=True)
        ws  = wb.active
        resultado = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row[0] or not row[1]: continue
            resultado[_fmt_fecha_xlsx(row[0])] = float(row[1])
        wb.close()
        return resultado
    except Exception as e:
        print(f"Error leyendo Excel dolar todos: {e}")
        return {}


def normalizar_ibc(fechas, valores):
    """
    Normaliza la serie del IBC aplicando ÷1000 a los valores pre-rebase BVC.
    La BVC rebasó su índice el 2025-07-28 (de escala ~500.000 a ~500).
    Detecta el quiebre automáticamente (caída > 85% entre sesiones).
    """
    if len(valores) < 2:
        return valores
    idx_quiebre = None
    for i in range(1, len(valores)):
        prev = valores[i-1]
        curr = valores[i]
        if prev and curr and prev > 0:
            if (prev - curr) / prev > 0.85:
                idx_quiebre = i
                break
    if idx_quiebre is None:
        return valores
    print(f"⚙️  Rebase BVC detectado entre {fechas[idx_quiebre-1]} → {fechas[idx_quiebre]}. "
          f"Normalizando {idx_quiebre} registros ÷1000.")
    ajustados = list(valores)
    for j in range(idx_quiebre):
        if ajustados[j] is not None:
            ajustados[j] = round(ajustados[j] / 1000, 2)
    return ajustados

# Permisos disponibles para asignar a usuarios
PERMISOS_DISPONIBLES = {
    'ver_mercado':         'Ver Mercado Principal',
    'ver_rankings':        'Ver Rankings',
    'ver_analisis':        'Ver Análisis Técnico',
    'ver_consulta':        'Ver Consulta de Acciones',
    'ver_indices':         'Ver Índices',
    'ver_rankings_fechas': 'Ver Rankings por Fechas',
}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Feriados ---
def cargar_fechas_feriadas():
    fechas_feriadas = set()
    if os.path.exists(FERIADOS_CSV):
        try:
            with open(FERIADOS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        fecha_obj = datetime.strptime(row['Fecha'], '%d/%m/%Y')
                        fechas_feriadas.add(fecha_obj.strftime('%Y-%m-%d'))
                    except ValueError:
                        continue
        except Exception as e:
            print(f"Error cargando feriados: {e}")
    return fechas_feriadas

FECHAS_FERIADAS = cargar_fechas_feriadas()

# ========== HELPERS ==========
def format_spanish(value, decimals=2):
    try:
        if value is None: return "0,00"
        return f"{float(value):,.{decimals}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except: return str(value)

def tiene_imagen(simbolo):
    return os.path.exists(os.path.join(BASE_DIR, f"static/img/acciones/{simbolo}.png"))

app.jinja_env.globals.update(format_spanish=format_spanish, tiene_imagen=tiene_imagen)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ========== CREAR TABLA USUARIOS ==========
def crear_tabla_usuarios():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT,
        activo INTEGER DEFAULT 1,
        permisos TEXT DEFAULT '',
        fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

crear_tabla_usuarios()

# ========== DECORADORES ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def permiso_requerido(permiso):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_logged_in' in session:
                return f(*args, **kwargs)
            if 'user_logged_in' not in session:
                return redirect(url_for('login'))
            if permiso not in session.get('permisos', []):
                return render_template('sin_permiso.html'), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_permiso_requerido(permiso):
    """
    Igual que permiso_requerido pero para endpoints /api/...
    Devuelve JSON en lugar de redirect/HTML para no romper el fetch() del frontend.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_logged_in' in session:
                return f(*args, **kwargs)
            if 'user_logged_in' not in session:
                return jsonify({"error": "no_session", "message": "Sesión expirada. Por favor inicia sesión nuevamente."}), 401
            if permiso not in session.get('permisos', []):
                return jsonify({"error": "sin_permiso", "message": "No tienes permiso para acceder a esta sección."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_user():
    return dict(
        is_admin='admin_logged_in' in session,
        is_user='user_logged_in' in session,
        current_user=session.get('username'),
        user_permisos=session.get('permisos', [])
    )

# ========== RSI ==========
def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo: return 50.0
    subidas, bajadas = [], []
    for i in range(1, len(precios)):
        dif = precios[i] - precios[i-1]
        subidas.append(max(0, dif))
        bajadas.append(max(0, -dif))
    avg_g = sum(subidas[-periodo:]) / periodo
    avg_p = sum(bajadas[-periodo:]) / periodo
    if avg_p == 0: return 100.0
    return 100 - (100 / (1 + avg_g / avg_p))

def obtener_datos_bvc(simbolo):
    url = f"https://market.bolsadecaracas.com/api/mercado/resumen/simbolos/{simbolo}/libroOrdenes"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, verify=False, timeout=5)
        if r.status_code == 200: return r.json()
    except: pass
    return None

# ========== AUTENTICACIÓN ==========

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USER and password == ADMIN_PASS:
            session['admin_logged_in'] = True
            session['username'] = username
            return redirect(url_for('admin_panel'))

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username = ? AND activo = 1", (username,)
        ).fetchone()
        conn.close()

        if user and user['password'] == hash_password(password):
            session['user_logged_in'] = True
            session['username'] = username
            session['permisos'] = user['permisos'].split(',') if user['permisos'] else []
            return redirect(url_for('index'))

        return render_template('login.html', error="Credenciales incorrectas")
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email    = request.form.get('email', '').strip()
        if not username or not password:
            return render_template('registro.html', error="Usuario y contraseña son obligatorios.")
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO usuarios (username, password, email, permisos) VALUES (?, ?, ?, ?)",
                (username, hash_password(password), email, '')
            )
            conn.commit()
            conn.close()
            return render_template('registro.html', success="¡Cuenta creada! Ya puedes iniciar sesión.")
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('registro.html', error="Ese nombre de usuario ya está en uso.")
    return render_template('registro.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ========== ADMIN ==========

@app.route('/admin')
@login_required
def admin_panel():
    conn = get_db()
    usuarios = [dict(u) for u in conn.execute("SELECT * FROM usuarios ORDER BY fecha_registro DESC").fetchall()]
    conn.close()
    return render_template('panel.html',
                           current_date=datetime.now().strftime('%Y-%m-%d'),
                           usuarios=usuarios,
                           permisos_disponibles=PERMISOS_DISPONIBLES)

@app.route('/admin/guardar', methods=['POST'])
@login_required
def admin_guardar():
    fecha    = request.form.get('fecha')
    simbolo  = request.form.get('simbolo').upper()
    nombre   = request.form.get('nombre')
    apertura = float(request.form.get('apertura', 0))
    cierre   = float(request.form.get('cierre', 0))
    maximo   = float(request.form.get('maximo', 0))
    minimo   = float(request.form.get('minimo', 0))
    volumen  = float(request.form.get('volumen', 0))
    variacion = ((cierre - apertura) / apertura) * 100 if apertura > 0 else 0
    conn = get_db()
    try:
        conn.execute("""INSERT OR REPLACE INTO mercado
            (fecha, simbolo, nombre, apertura, maximo, minimo, cierre, volumen, variacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (fecha, simbolo, nombre, apertura, maximo, minimo, cierre, volumen, variacion))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/admin/usuarios/permisos', methods=['POST'])
@login_required
def admin_actualizar_permisos():
    data     = request.json
    user_id  = data.get('user_id')
    permisos = ','.join(data.get('permisos', []))
    conn = get_db()
    conn.execute("UPDATE usuarios SET permisos = ? WHERE id = ?", (permisos, user_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/admin/usuarios/toggle', methods=['POST'])
@login_required
def admin_toggle_usuario():
    user_id = request.json.get('user_id')
    conn = get_db()
    conn.execute("UPDATE usuarios SET activo = CASE WHEN activo=1 THEN 0 ELSE 1 END WHERE id=?", (user_id,))
    conn.commit()
    row = conn.execute("SELECT activo FROM usuarios WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return jsonify({"status": "ok", "activo": row['activo']})

@app.route('/admin/usuarios/eliminar', methods=['POST'])
@login_required
def admin_eliminar_usuario():
    conn = get_db()
    conn.execute("DELETE FROM usuarios WHERE id=?", (request.json.get('user_id'),))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

# ========== RUTAS PÚBLICAS ==========

@app.route('/')
def index():
    conn = get_db()
    lista_fechas = [r[0] for r in conn.execute("SELECT DISTINCT fecha FROM mercado WHERE fecha >= '2024-01-01' ORDER BY fecha DESC").fetchall()]
    fecha_actual = request.args.get('fecha', lista_fechas[0] if lista_fechas else None)
    acciones, stats = [], {'suben': 0, 'bajan': 0, 'estables': 0, 'total': 0}
    if fecha_actual:
        rows = conn.execute("SELECT * FROM mercado WHERE fecha=? ORDER BY simbolo", (fecha_actual,)).fetchall()
        acciones = [dict(r) for r in rows]
        stats = {
            'total': len(acciones),
            'suben': sum(1 for a in acciones if a['variacion'] > 0),
            'bajan': sum(1 for a in acciones if a['variacion'] < 0),
            'estables': sum(1 for a in acciones if a['variacion'] == 0)
        }
    conn.close()
    return render_template('index.html', acciones=acciones, fecha_actual=fecha_actual,
                           lista_fechas=lista_fechas, estadisticas=stats)

@app.route('/analisis-tecnico')
@permiso_requerido('ver_analisis')
def vista_analisis_tecnico():
    return render_template('analisis_tecnico.html')

@app.route('/consulta')
@permiso_requerido('ver_consulta')
def consulta():
    conn = get_db()
    acciones = [dict(r) for r in conn.execute("""
        SELECT simbolo, nombre FROM mercado
        WHERE cierre > 0
        GROUP BY simbolo
        HAVING MAX(fecha) >= date('now', '-6 months')
        ORDER BY simbolo
    """).fetchall()]
    conn.close()
    return render_template('consulta.html', acciones=acciones)

@app.route('/rankings')
@permiso_requerido('ver_rankings')
def vista_rankings():
    periodos = {
        '1_Semana': {'label': '1 Semana',  'dias_objetivo': 7,   'margen': 3},
        '1_Mes':    {'label': '1 Mes',      'dias_objetivo': 30,  'margen': 5},
        '3_Meses':  {'label': '3 Meses',    'dias_objetivo': 90,  'margen': 8},
        '6_Meses':  {'label': '6 Meses',    'dias_objetivo': 180, 'margen': 10},
        '1_Año':    {'label': '1 Año',      'dias_objetivo': 365, 'margen': 15}
    }
    rankings_data = {}
    conn = get_db()
    ultima_fecha = conn.execute("SELECT MAX(fecha) FROM mercado").fetchone()[0]

    rows_dia = conn.execute(f"""
        SELECT simbolo, nombre, apertura, cierre, volumen,
               ((cierre - apertura) / apertura) * 100 as variacion
        FROM mercado WHERE fecha = '{ultima_fecha}' AND apertura > 0
    """).fetchall()
    data_dia = [dict(r) for r in rows_dia]

    rankings_data['Dia'] = {
        'titulo': 'Hoy', 'rango': f"Sesión del {ultima_fecha}",
        'ganadoras':  sorted([x for x in data_dia if x['variacion'] > 0.01], key=lambda x: x['variacion'], reverse=True)[:5],
        'perdedoras': sorted([x for x in data_dia if x['variacion'] < -0.01], key=lambda x: x['variacion'])[:5],
        'mas_negociadas':   sorted(data_dia, key=lambda x: x['volumen'] or 0, reverse=True)[:5],
        'menos_negociadas': sorted([x for x in data_dia if x['volumen'] > 0], key=lambda x: x['volumen'])[:5],
        'labels': [], 'valores': []
    }
    g = rankings_data['Dia']['ganadoras']; p = rankings_data['Dia']['perdedoras']
    rankings_data['Dia']['labels'] = [x['simbolo'] for x in g + p]
    rankings_data['Dia']['valores'] = [round(float(x['variacion']), 2) for x in g + p]

    for key, info in periodos.items():
        rows = conn.execute(f"""
            WITH RangoFechas AS (
                SELECT simbolo, SUM(volumen) as volumen_total FROM mercado
                WHERE julianday('{ultima_fecha}') - julianday(fecha) <= {info['dias_objetivo']} GROUP BY simbolo
            ),
            PrecioActual AS (SELECT simbolo, cierre FROM mercado WHERE fecha = '{ultima_fecha}'),
            PrecioPasado AS (
                SELECT simbolo, apertura, fecha,
                ROW_NUMBER() OVER (PARTITION BY simbolo ORDER BY ABS(julianday('{ultima_fecha}') - julianday(fecha) - {info['dias_objetivo']}) ASC) as rn
                FROM mercado
                WHERE julianday('{ultima_fecha}') - julianday(fecha)
                      BETWEEN {info['dias_objetivo'] - info['margen']} AND {info['dias_objetivo'] + info['margen']}
            )
            SELECT a.simbolo, a.cierre as actual, p.apertura as pasado, p.fecha as fecha_inicio,
                   ((a.cierre - p.apertura) / p.apertura) * 100 as rendimiento, rf.volumen_total
            FROM PrecioActual a
            JOIN PrecioPasado p ON a.simbolo = p.simbolo
            JOIN RangoFechas rf ON a.simbolo = rf.simbolo
            WHERE p.rn = 1 AND p.apertura > 0
        """).fetchall()
        data = [dict(r) for r in rows]
        g2 = sorted([x for x in data if x['rendimiento'] > 0.01], key=lambda x: x['rendimiento'], reverse=True)[:5]
        p2 = sorted([x for x in data if x['rendimiento'] < -0.01], key=lambda x: x['rendimiento'])[:5]
        rankings_data[key] = {
            'titulo': info['label'],
            'rango': f"Desde {data[0]['fecha_inicio'] if data else 'N/A'} hasta {ultima_fecha}",
            'ganadoras': g2, 'perdedoras': p2,
            'mas_negociadas':   sorted(data, key=lambda x: x['volumen_total'] or 0, reverse=True)[:5],
            'menos_negociadas': sorted([x for x in data if x['volumen_total'] > 0], key=lambda x: x['volumen_total'])[:5],
            'labels': [x['simbolo'] for x in g2 + p2],
            'valores': [round(float(x['rendimiento']), 2) for x in g2 + p2]
        }

    conn.close()
    return render_template('rankings.html', rankings=rankings_data)

# ========== RANKINGS POR FECHAS PERSONALIZADAS ==========

@app.route('/rankings-fechas')
@permiso_requerido('ver_rankings_fechas')
def vista_rankings_fechas():
    conn = get_db()
    fechas_disponibles = [r[0] for r in conn.execute(
        "SELECT DISTINCT fecha FROM mercado ORDER BY fecha DESC"
    ).fetchall()]
    conn.close()
    return render_template('rankings_fechas.html', fechas_disponibles=fechas_disponibles)

@app.route('/api/rankings-fechas')
def api_rankings_fechas():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin    = request.args.get('fecha_fin')
    if not fecha_inicio or not fecha_fin:
        return jsonify({"error": "Parámetros incompletos"}), 400

    conn = get_db()
    rows = conn.execute("""
        WITH PrecioInicio AS (
            SELECT simbolo, nombre, apertura, fecha as f_inicio,
                   ROW_NUMBER() OVER (PARTITION BY simbolo ORDER BY fecha ASC) as rn
            FROM mercado WHERE fecha >= ? AND apertura > 0
        ),
        PrecioFin AS (
            SELECT simbolo, cierre, fecha as f_fin,
                   ROW_NUMBER() OVER (PARTITION BY simbolo ORDER BY fecha DESC) as rn
            FROM mercado WHERE fecha <= ?
        ),
        Volumen AS (
            SELECT simbolo, SUM(volumen) as volumen_total
            FROM mercado WHERE fecha BETWEEN ? AND ? GROUP BY simbolo
        )
        SELECT pi.simbolo, pi.nombre, pi.apertura as precio_inicio, pf.cierre as precio_fin,
               pi.f_inicio, pf.f_fin,
               ((pf.cierre - pi.apertura) / pi.apertura) * 100 as rendimiento,
               v.volumen_total
        FROM PrecioInicio pi
        JOIN PrecioFin pf ON pi.simbolo = pf.simbolo AND pi.rn=1 AND pf.rn=1
        JOIN Volumen v ON pi.simbolo = v.simbolo
        WHERE pi.apertura > 0
        ORDER BY rendimiento DESC
    """, (fecha_inicio, fecha_fin, fecha_inicio, fecha_fin)).fetchall()
    data = [dict(r) for r in rows]

    conn.close()
    return jsonify({
        "ganadoras":      sorted([x for x in data if x['rendimiento'] > 0.01], key=lambda x: x['rendimiento'], reverse=True)[:10],
        "perdedoras":     sorted([x for x in data if x['rendimiento'] < -0.01], key=lambda x: x['rendimiento'])[:10],
        "mas_negociadas": sorted(data, key=lambda x: x['volumen_total'] or 0, reverse=True)[:10],
        "menos_negociadas": sorted([x for x in data if x['volumen_total'] > 0], key=lambda x: x['volumen_total'])[:10],
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "total": len(data)
    })

# ========== ÍNDICES ==========

@app.route('/indices')
@permiso_requerido('ver_indices')
def vista_indices():
    return render_template('indices.html')

@app.route('/api/indices')
def api_indices():
    dias = request.args.get('dias', default=7, type=int)
    conn = get_db()
    indices = conn.execute('SELECT fecha, dolar, ibc FROM indicadores ORDER BY fecha DESC LIMIT ?', (dias,)).fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in reversed(indices)])

@app.route('/api/ultimo_indice')
def api_ultimo_indice():
    conn = get_db()
    res = conn.execute('SELECT * FROM indicadores ORDER BY fecha DESC LIMIT 1').fetchone()
    conn.close()
    return jsonify(dict(res)) if res else jsonify({"ibc": 0, "dolar": 0, "fecha": "N/A"})

@app.route('/api/indices-hoy')
def api_indices_hoy():
    """Datos del día: IBC de tabla 'indices' (último registro) + dólar del Excel"""
    resultado = {
        'ibc': None, 'ibc_var': None, 'ibc_var_pct': None,
        'dolar': None, 'dolar_var_pct': None, 'ibc_usd': None,
        'fecha': None, 'fecha_dolar': None, 'archivo_dat': None,
        'fuente_ibc': None, 'fuente_dolar': None
    }

    def fecha_int_a_str(f):
        """Convierte 20251226 → '2025-12-26'"""
        f = str(int(f))
        return f"{f[:4]}-{f[4:6]}-{f[6:]}" if len(f) == 8 else f

    # ── IBC: último registro de tabla 'indices' (YYYYMMDD entero) ──
    conn = get_db()
    row_ibc = conn.execute(
        "SELECT fecha, valor, variacion FROM indices WHERE valor > 0 ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    row_ibc_prev = conn.execute(
        "SELECT valor FROM indices WHERE valor > 0 ORDER BY fecha DESC LIMIT 1 OFFSET 1"
    ).fetchone()
    conn.close()

    if row_ibc and row_ibc['valor']:
        resultado['fecha']      = fecha_int_a_str(row_ibc['fecha'])
        resultado['ibc']        = round(row_ibc['valor'], 2)
        resultado['fuente_ibc'] = 'db'
        # Variación absoluta guardada en la tabla
        var_abs = row_ibc['variacion'] if row_ibc['variacion'] is not None else 0
        resultado['ibc_var'] = round(var_abs, 2)
        # Variación porcentual calculada desde el registro anterior
        if row_ibc_prev and row_ibc_prev['valor'] and row_ibc_prev['valor'] > 0:
            resultado['ibc_var_pct'] = round(
                (row_ibc['valor'] - row_ibc_prev['valor']) / row_ibc_prev['valor'] * 100, 2
            )
        else:
            resultado['ibc_var_pct'] = 0.0

    # ── Fallback: archivo .dat si no hay datos en BD ──
    if resultado['ibc'] is None:
        ruta_dat = buscar_dat_reciente()
        if ruta_dat:
            datos_dat = leer_ibc_de_dat(ruta_dat)
            if datos_dat and datos_dat['ibc'] > 0:
                resultado['ibc']         = round(datos_dat['ibc'], 2)
                resultado['ibc_var']     = round(datos_dat['ibc_var'], 2)
                resultado['ibc_var_pct'] = round(datos_dat['ibc_var_pct'], 2)
                resultado['fecha']       = datos_dat['fecha']
                resultado['archivo_dat'] = datos_dat['archivo']
                resultado['fuente_ibc']  = 'dat'

    # ── Dólar: primero tabla indicadores, luego fallback Excel ──
    conn2 = get_db()
    row_dolar = conn2.execute(
        "SELECT fecha, dolar FROM indicadores WHERE dolar > 0 ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    row_dolar_prev = conn2.execute(
        "SELECT dolar FROM indicadores WHERE dolar > 0 ORDER BY fecha DESC LIMIT 1 OFFSET 1"
    ).fetchone()
    conn2.close()

    if row_dolar and row_dolar['dolar']:
        dolar_val  = round(row_dolar['dolar'], 4)
        dolar_prev = row_dolar_prev['dolar'] if row_dolar_prev else None
        var_pct    = round((dolar_val - dolar_prev) / dolar_prev * 100, 4) if dolar_prev and dolar_prev > 0 else 0.0
        resultado['dolar']         = dolar_val
        resultado['dolar_var_pct'] = var_pct
        resultado['fecha_dolar']   = row_dolar['fecha']
        resultado['fuente_dolar']  = 'bd'
    else:
        fecha_buscar = resultado.get('fecha')
        datos_dolar  = leer_dolar_de_xlsx(fecha_buscar) if fecha_buscar else None
        if not datos_dolar:
            datos_dolar = leer_dolar_de_xlsx()
        if datos_dolar:
            resultado['dolar']         = round(datos_dolar['tasa'], 4)
            resultado['dolar_var_pct'] = round(datos_dolar.get('variacion_pct', 0), 4)
            resultado['fecha_dolar']   = datos_dolar['fecha']
            resultado['fuente_dolar']  = 'xlsx'

    # ── IBC en USD ──
    if resultado['ibc'] and resultado['dolar'] and resultado['dolar'] > 0:
        resultado['ibc_usd'] = round(resultado['ibc'] / resultado['dolar'], 4)

    return jsonify(resultado)


@app.route('/api/comparativa-indices')
def api_comparativa_indices():
    """
    Serie histórica de IBC desde tabla 'indices'
    + Dólar desde tabla 'indicadores' (con fallback al Excel).
    """
    def fecha_int_a_str(f):
        f = str(int(f))
        return f"{f[:4]}-{f[4:6]}-{f[6:]}" if len(f) == 8 else f

    conn = get_db()
    rows = conn.execute(
        "SELECT fecha, valor FROM indices WHERE valor > 0 ORDER BY fecha ASC"
    ).fetchall()
    dolar_rows = conn.execute(
        "SELECT fecha, dolar FROM indicadores WHERE dolar > 0 ORDER BY fecha ASC"
    ).fetchall()
    conn.close()

    dolar_bd   = {r['fecha']: r['dolar'] for r in dolar_rows}
    dolar_xlsx = leer_todos_dolar_xlsx()

    fechas        = []
    valores_ibc   = []
    valores_dolar = []

    for r in rows:
        fecha_str = fecha_int_a_str(r['fecha'])
        fechas.append(fecha_str)
        valores_ibc.append(round(r['valor'], 2))
        valores_dolar.append(dolar_bd.get(fecha_str) or dolar_xlsx.get(fecha_str) or None)

    valores_ibc = normalizar_ibc(fechas, valores_ibc)

    return jsonify({
        'fechas':        fechas,
        'valores_ibc':   valores_ibc,
        'valores_dolar': valores_dolar
    })
# ========== ADMIN: TABLA INDICES ==========

@app.route('/admin/guardar_indice_manual', methods=['POST'])
@login_required
def admin_guardar_indice_manual():
    """Guarda o actualiza un registro IBC en la tabla indices"""
    data      = request.json
    fecha_str = str(data.get('fecha', '')).replace('-', '')   # YYYY-MM-DD → YYYYMMDD int
    valor     = float(data.get('valor', 0))
    variacion = float(data.get('variacion', 0))
    fuente    = data.get('fuente', 'manual')
    if not fecha_str or not valor:
        return jsonify({"status": "error", "message": "Fecha y valor son requeridos"}), 400
    conn = get_db()
    try:
        existente = conn.execute(
            "SELECT id FROM indices WHERE fecha = ?", (int(fecha_str),)
        ).fetchone()
        if existente:
            conn.execute(
                "UPDATE indices SET valor=?, variacion=?, fuente=?, created_at=datetime('now') WHERE fecha=?",
                (valor, variacion, fuente, int(fecha_str))
            )
        else:
            conn.execute(
                "INSERT INTO indices (fecha, valor, variacion, fuente, created_at) VALUES (?,?,?,?,datetime('now'))",
                (int(fecha_str), valor, variacion, fuente)
            )
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "fecha": fecha_str, "valor": valor})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/eliminar_indice_manual', methods=['POST'])
@login_required
def admin_eliminar_indice_manual():
    """Elimina un registro de la tabla indices por fecha"""
    data      = request.json
    fecha_str = str(data.get('fecha', '')).replace('-', '')
    conn      = get_db()
    conn.execute("DELETE FROM indices WHERE fecha=?", (int(fecha_str),))
    conn.commit(); conn.close()
    return jsonify({"status": "ok"})

@app.route('/admin/historial_indices')
@login_required
def admin_historial_indices():
    """Últimos registros de la tabla indices para mostrar en panel admin"""
    limit = request.args.get('limit', 15, type=int)
    conn  = get_db()
    rows  = conn.execute(
        "SELECT id, fecha, valor, variacion, fuente, created_at FROM indices ORDER BY fecha DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    def fmt(f):
        f = str(f)
        return f"{f[:4]}-{f[4:6]}-{f[6:]}" if len(f) == 8 else f
    return jsonify([{
        'id':         r['id'],
        'fecha':      fmt(r['fecha']),
        'valor':      r['valor'],
        'variacion':  r['variacion'],
        'fuente':     r['fuente'],
        'created_at': r['created_at']
    } for r in rows])



# ========== API: HISTÓRICO DE ACCIONES (para consulta.html) ==========

@app.route('/api/historico')
@api_permiso_requerido('ver_consulta')
def api_historico():
    """
    Devuelve el histórico completo de una acción desde la tabla 'mercado'.
    Responde con { datos: [...], actual: {...} }
    Cada registro: { fecha, simbolo, nombre, apertura, maximo, minimo, cierre, volumen, variacion }
    """
    simbolo = request.args.get('simbolo', '').upper().strip()
    if not simbolo:
        return jsonify({"error": "Parámetro 'simbolo' requerido"}), 400

    conn = get_db()
    rows = conn.execute("""
        SELECT fecha, simbolo, nombre, apertura, maximo, minimo, cierre, volumen, variacion
        FROM mercado
        WHERE simbolo = ? AND cierre > 0
        ORDER BY fecha ASC
    """, (simbolo,)).fetchall()
    conn.close()

    datos = [dict(r) for r in rows]
    actual = datos[-1] if datos else {}

    return jsonify({"datos": datos, "actual": actual})


@app.route('/api/libro-ordenes/<simbolo>')
@api_permiso_requerido('ver_consulta')
def api_libro_ordenes(simbolo):
    """
    Proxy al libro de órdenes de la BVC para un símbolo dado.
    Responde con { success: bool, datos: [...] }
    """
    simbolo = simbolo.upper().strip()
    datos_bvc = obtener_datos_bvc(simbolo)
    if datos_bvc is None:
        return jsonify({"success": False, "datos": [], "error": "No se pudo conectar con la BVC"}), 200

    # La API BVC devuelve una lista directamente o un dict con 'data'/'ordenes'
    if isinstance(datos_bvc, list):
        return jsonify({"success": True, "datos": datos_bvc})
    elif isinstance(datos_bvc, dict):
        # Intentar extraer la lista de órdenes del formato conocido
        for key in ('ordenes', 'data', 'libroOrdenes', 'items'):
            if key in datos_bvc and isinstance(datos_bvc[key], list):
                return jsonify({"success": True, "datos": datos_bvc[key]})
        # Si no encontramos la clave, devolver el dict como lista de un elemento
        return jsonify({"success": True, "datos": [datos_bvc]})

    return jsonify({"success": False, "datos": [], "error": "Formato de respuesta inesperado"}), 200


# ========== ADMIN: DÓLAR BCV (tabla indicadores) ==========

@app.route('/admin/guardar_dolar', methods=['POST'])
@login_required
def admin_guardar_dolar():
    """Guarda o actualiza el dólar BCV en la columna 'dolar' de tabla indicadores"""
    data  = request.json
    fecha = data.get('fecha', '')   # viene como YYYY-MM-DD
    valor = float(data.get('valor', 0))
    if not fecha or not valor:
        return jsonify({"status": "error", "message": "Fecha y valor son requeridos"}), 400
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO indicadores (fecha, dolar, ibc)
            VALUES (?, ?, 0)
            ON CONFLICT(fecha) DO UPDATE SET dolar = excluded.dolar
        ''', (fecha, valor))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "fecha": fecha, "valor": valor})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/admin/obtener_historial_indices/<tipo>')
@login_required
def admin_obtener_historial_indices(tipo):
    """Devuelve los últimos registros de dólar o ibc de la tabla indicadores"""
    conn = get_db()
    if tipo == 'dolar':
        rows = conn.execute(
            "SELECT fecha, dolar as valor FROM indicadores WHERE dolar > 0 ORDER BY fecha DESC LIMIT 15"
        ).fetchall()
    elif tipo == 'ibc':
        rows = conn.execute(
            "SELECT fecha, ibc as valor FROM indicadores WHERE ibc > 0 ORDER BY fecha DESC LIMIT 15"
        ).fetchall()
    else:
        conn.close()
        return jsonify([])
    conn.close()
    return jsonify([{"fecha": r["fecha"], "valor": r["valor"]} for r in rows])


@app.route('/admin/eliminar_indice', methods=['POST'])
@login_required
def admin_eliminar_indice():
    """Pone en 0 el dólar o el ibc de un registro en tabla indicadores"""
    data  = request.json
    tipo  = data.get('tipo')   # 'dolar' o 'ibc'
    fecha = data.get('fecha')  # YYYY-MM-DD
    if tipo not in ('dolar', 'ibc') or not fecha:
        return jsonify({"status": "error", "message": "Parámetros inválidos"}), 400
    conn = get_db()
    try:
        conn.execute(f"UPDATE indicadores SET {tipo} = 0 WHERE fecha = ?", (fecha,))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 500



# ========== ADMIN: ENDPOINTS FALTANTES ==========

@app.route('/admin/obtener_registros/<fecha>')
@login_required
def admin_obtener_registros(fecha):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM mercado WHERE fecha = ? ORDER BY simbolo", (fecha,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/admin/guardar_masivo', methods=['POST'])
@login_required
def admin_guardar_masivo():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({"status": "error", "message": "Datos inválidos"}), 400
    conn = get_db()
    try:
        for reg in data:
            fecha    = reg.get('fecha', '')
            simbolo  = reg.get('simbolo', '').upper().strip()
            apertura = float(reg.get('apertura', 0) or 0)
            maximo   = float(reg.get('maximo', 0) or 0)
            minimo   = float(reg.get('minimo', 0) or 0)
            cierre   = float(reg.get('cierre', 0) or 0)
            volumen  = float(reg.get('volumen', 0) or 0)
            variacion = ((cierre - apertura) / apertura) * 100 if apertura > 0 else 0
            if not fecha or not simbolo:
                continue
            conn.execute("""
                INSERT OR REPLACE INTO mercado
                (fecha, simbolo, nombre, apertura, maximo, minimo, cierre, volumen, variacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (fecha, simbolo, reg.get('nombre', simbolo), apertura, maximo, minimo, cierre, volumen, variacion))
        conn.commit()
        conn.close()
        return jsonify({"status": "ok", "guardados": len(data)})
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/admin/eliminar_registro', methods=['POST'])
@login_required
def admin_eliminar_registro():
    data    = request.json
    fecha   = data.get('fecha', '')
    simbolo = data.get('simbolo', '').upper().strip()
    if not fecha or not simbolo:
        return jsonify({"status": "error", "message": "Fecha y símbolo requeridos"}), 400
    conn = get_db()
    conn.execute("DELETE FROM mercado WHERE fecha = ? AND simbolo = ?", (fecha, simbolo))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


@app.route('/admin/historial_dolar')
@login_required
def admin_historial_dolar():
    limit = request.args.get('limit', 10, type=int)
    conn  = get_db()
    rows  = conn.execute(
        "SELECT fecha, dolar as valor FROM indicadores WHERE dolar > 0 ORDER BY fecha DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return jsonify([{"fecha": r["fecha"], "valor": r["valor"]} for r in rows])


@app.route('/admin/cargar_masivo', methods=['GET', 'POST'])
@login_required
def admin_cargar_masivo():
    if request.method == 'GET':
        return redirect(url_for('admin_panel'))
    archivos = request.files.getlist('archivos')
    procesados = 0
    errores = []
    for archivo in archivos:
        if archivo and archivo.filename.lower().endswith('.dat'):
            ruta_tmp = os.path.join(DATA_DIR, archivo.filename)
            os.makedirs(DATA_DIR, exist_ok=True)
            archivo.save(ruta_tmp)
            if data_manager.procesar_dat(ruta_tmp):
                procesados += 1
            else:
                errores.append(archivo.filename)
    return jsonify({"status": "ok", "procesados": procesados, "errores": errores})

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)