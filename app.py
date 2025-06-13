from flask import Flask
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import datetime
import requests
import pytz

# --- Configurações da VM e FIWARE (Estes são os DADOS da sua VM) ---
# ATENÇÃO: VERIFIQUE E CONFIRME ESTE IP!
VM_IP_ADDRESS = "130.131.16.56" # <--- **CONFIRME ESTE IP!**
PORT_STH = 8666 # Porta padrão do STH-Comet na VM
FIWARE_SERVICE = 'smart' # Conforme seu exemplo de configuração Fiware
FIWARE_SERVICE_PATH = '/' # Conforme seu exemplo de configuração Fiware

# ID e Tipo da entidade conforme o JSON do seu dispositivo
NEXUSCODE_DEVICE_ID = "urn:ngsi-ld:NEXUScode:003"
NEXUSCODE_ENTITY_TYPE = "Acess" # <--- **MUITO IMPORTANTE! CONFIRMADO como "Acess"**

# Atributos que você quer exibir no dashboard
ATTRIBUTES_TO_FETCH = ['state', 'permitido', 'negado', 'aberto', 'fechado']

# Headers para as requisições ao FIWARE
FIWARE_HEADERS = {
    'fiware-service': FIWARE_SERVICE,
    'fiware-servicepath': FIWARE_SERVICE_PATH
}

# --- Funções de Coleta de Dados do FIWARE (Fazem requisição para a VM) ---
def get_device_data_from_fiware():
    """Função para obter os dados do dispositivo NEXUScode3 do FIWARE (STH-Comet)."""
    data = {}
    for attr in ATTRIBUTES_TO_FETCH:
        # CONSTRÓI A URL EXATAMENTE COMO NO SEU POSTMAN, USANDO AS VARIÁVEIS ACIMA
        url = f"http://{VM_IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/{NEXUSCODE_ENTITY_TYPE}/id/{NEXUSCODE_DEVICE_ID}/attributes/{attr}?lastN=1"
        
        print(f"Tentando acessar URL: {url}") # Para depuração

        try:
            response = requests.get(url, headers=FIWARE_HEADERS, timeout=10) # Aumentei o timeout
            response.raise_for_status() # Lança uma exceção para códigos de status HTTP de erro (4xx ou 5xx)
            json_data = response.json()
            
            # Navegar na estrutura da resposta para obter o valor
            if 'contextResponses' in json_data and json_data['contextResponses']:
                context_element = json_data['contextResponses'][0]['contextElement']
                if 'attributes' in context_element and context_element['attributes']:
                    attribute_data = context_element['attributes'][0]
                    if 'values' in attribute_data and attribute_data['values']:
                        # Pega o último valor (o mais recente)
                        data[attr] = attribute_data['values'][0]['attrValue']
                    else:
                        data[attr] = "N/A" # Atributo sem valores
            else:
                data[attr] = "N/A" # Estrutura de resposta inesperada
        except requests.exceptions.HTTPError as http_err:
            print(f"Erro HTTP ao acessar Fiware STH-Comet para o atributo {attr}: {http_err} - Resposta: {response.text if response else 'N/A'}")
            data[attr] = f"Erro HTTP: {http_err.response.status_code}"
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Erro de Conexão ao acessar Fiware STH-Comet para o atributo {attr}: {conn_err}")
            data[attr] = f"Erro de Conexão: {conn_err}"
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout ao acessar Fiware STH-Comet para o atributo {attr}: {timeout_err}")
            data[attr] = f"Timeout"
        except requests.exceptions.RequestException as req_err:
            print(f"Erro Inesperado ao acessar Fiware STH-Comet para o atributo {attr}: {req_err}")
            data[attr] = f"Erro de Requisição: {req_err}"
        except (KeyError, IndexError, ValueError) as e: # ValueError para JSON parsing
            print(f"Erro ao processar a resposta JSON do Fiware para o atributo {attr}: {e}")
            data[attr] = "Erro de Formato JSON"
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
        # Este é o catch-all para qualquer erro inesperado.
        # Os catches mais específicos na função get_device_data_from_fiware()
        # deverão pegar a maioria dos erros de requisição.
        print(f"Erro geral no callback de atualização: {e}")
        return [f"Erro interno no dashboard: {e}"] * 6

# Inicia o servidor Flask na porta 5000, na sua máquina local.
if __name__ == "__main__":
    server.run(debug=True, host="0.0.0.0", port=5000)

print("Servidor rodando em http://localhost:5000/dashboard/")