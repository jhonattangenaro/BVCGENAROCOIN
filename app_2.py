from flask import Flask, render_template, request
import requests
import urllib3

# Desactivar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

def obtener_datos_bvc(simbolo):
    url = f"https://market.bolsadecaracas.com/api/mercado/resumen/simbolos/{simbolo}/libroOrdenes"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # verify=False para evitar tu error de certificados en Windows
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error: {e}")
    return None

@app.route('/', methods=['GET', 'POST'])
def index():
    datos = None
    simbolo_buscado = None
    
    # Lista de algunos símbolos comunes para el buscador (puedes añadir más)
    simbolos_sugeridos = ["RST", "BNC", "ABC", "EFE", "FVI.B", "MVZ.A", "TDV.D"]

    if request.method == 'POST':
        simbolo_buscado = request.form.get('simbolo').upper()
        datos = obtener_datos_bvc(simbolo_buscado)

    return render_template('index.html', datos=datos, simbolo=simbolo_buscado, sugerencias=simbolos_sugeridos)

if __name__ == '__main__':
    app.run(debug=True)