from flask import Flask
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import datetime
import requests
import pytz

# --- Configurações da VM e FIWARE (Estes são os DADOS da sua VM) ---
# ATENÇÃO: SUBSTITUA 'YOUR_VM_IP_ADDRESS' PELO ENDEREÇO IP REAL DA SUA VM
VM_IP_ADDRESS = "130.131.16.56" # <-- Este é o IP da SUA VM
PORT_STH = 8666 # Porta padrão do STH-Comet na VM
FIWARE_SERVICE = 'smart'
FIWARE_SERVICE_PATH = '/'
NEXUSCODE_DEVICE_ID = "urn:ngsi-ld:NEXUScode:003" # ID da sua entidade NEXUScode3 no Fiware
ATTRIBUTES_TO_FETCH = ['state', 'permitido', 'negado', 'aberto', 'fechado']

# Headers para as requisições ao FIWARE
FIWARE_HEADERS = {
    'fiware-service': FIWARE_SERVICE,
    'fiware-servicepath': FIWARE_SERVICE_PATH
}

# --- Funções de Coleta de Dados do FIWARE (Fazem requisição para a VM) ---
def get_device_data_from_fiware():
    data = {}
    for attr in ATTRIBUTES_TO_FETCH:
        url = f"http://{VM_IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/Device/id/{NEXUSCODE_DEVICE_ID}/attributes/{attr}?lastN=1"
        try:
            response = requests.get(url, headers=FIWARE_HEADERS, timeout=5)
            response.raise_for_status()
            json_data = response.json()
            
            if 'contextResponses' in json_data and json_data['contextResponses']:
                context_element = json_data['contextResponses'][0]['contextElement']
                if 'attributes' in context_element and context_element['attributes']:
                    attribute_data = context_element['attributes'][0]
                    if 'values' in attribute_data and attribute_data['values']:
                        data[attr] = attribute_data['values'][0]['attrValue']
                    else:
                        data[attr] = "N/A"
            else:
                data[attr] = "N/A"
        except requests.exceptions.RequestException as e:
            print(f"Erro ao acessar Fiware STH-Comet para o atributo {attr}: {e}")
            data[attr] = f"Erro: {e}"
        except (KeyError, IndexError) as e:
            print(f"Erro ao processar a resposta do Fiware para o atributo {attr}: {e}")
            data[attr] = "Erro de Formato"
    return data

# --- Criação do App Flask e Dash (Rodando na sua máquina local) ---
server = Flask(__name__)

app = dash.Dash(__name__, server=server, url_base_pathname="/dashboard/")
app.title = "NEXUScode3 Dashboard"

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
        data = get_device_data_from_fiware()

        state = data.get('state', 'Indefinido')
        permitido = data.get('permitido', '0')
        negado = data.get('negado', '0')
        aberto = data.get('aberto', '0')
        fechado = data.get('fechado', '0')

        return (
            f"Estado atual: {state}",
            f"Acessos Permitidos: {permitido}",
            f"Acessos Negados: {negado}",
            f"Aberturas: {aberto}",
            f"Fechamentos: {fechado}",
            f"Atualizado em: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )
    except Exception as e:
        return [f"Erro ao obter dados: {e}"] * 6

# Inicia o servidor Flask na porta 5000, na sua máquina local.
if __name__ == "__main__":
    server.run(debug=True, host="0.0.0.0", port=5000)