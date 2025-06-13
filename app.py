from flask import Flask, jsonify
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import datetime
import random

# Criação do app Flask
server = Flask(__name__)

# Rota de simulação para o dispositivo
@server.route("/api/v1/device/NEXUScode3", methods=["GET"])
def get_device_data():
    return jsonify({
        "state": random.choice(["aberto", "fechado", "espera"]),
        "permitido": str(random.randint(0, 10)),
        "negado": str(random.randint(0, 5)),
        "aberto": str(random.randint(0, 10)),
        "fechado": str(random.randint(0, 10))
    })

# App Dash com Flask
app = dash.Dash(__name__, server=server, url_base_pathname="/dashboard/")
app.title = "NEXUScode3 Dashboard"

# Endereço interno da API
API_URL = "http://localhost:8050/api/v1/device/NEXUScode3"

app.layout = html.Div([
    html.H1("Dashboard - NEXUScode3", style={"textAlign": "center"}),
    dcc.Interval(id="interval-component", interval=5000, n_intervals=0),
    html.Div([
        html.Div(id="estado"),
        html.Div(id="permitido"),
        html.Div(id="negado"),
        html.Div(id="aberto"),
        html.Div(id="fechado"),
        html.Div(id="timestamp", style={"marginTop": "10px", "fontStyle": "italic"})
    ], style={"textAlign": "center", "fontSize": 20, "marginTop": "40px"})
])

@app.callback(
    [Output("estado", "children"),
     Output("permitido", "children"),
     Output("negado", "children"),
     Output("aberto", "children"),
     Output("fechado", "children"),
     Output("timestamp", "children")],
    [Input("interval-component", "n_intervals")]
)
def update_dashboard(n):
    try:
        import requests
        response = requests.get(API_URL)
        data = response.json()

        return (
            f"Estado atual: {data.get('state', 'Indefinido')}",
            f"Acessos Permitidos: {data.get('permitido', '0')}",
            f"Acessos Negados: {data.get('negado', '0')}",
            f"Aberturas: {data.get('aberto', '0')}",
            f"Fechamentos: {data.get('fechado', '0')}",
            f"Atualizado em: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )
    except Exception as e:
        return [f"Erro ao obter dados: {e}"] * 6

# Inicia o servidor na porta 8050 (acessível externamente pela 5000)
if __name__ == "__main__":
    server.run(debug=True, host="0.0.0.0", port=8050)
