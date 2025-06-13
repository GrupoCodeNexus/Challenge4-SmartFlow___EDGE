from flask import Flask
import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output
import datetime
import requests
import pytz
import pandas as pd
import dash_bootstrap_components as dbc # Importa componentes Bootstrap

# --- Configurações da VM e FIWARE ---
VM_IP_ADDRESS = "130.131.16.56" # CONFIRME ESTE IP!
PORT_STH = 8666 # Porta padrão do STH-Comet na VM
PORT_ORION = 1026 # Porta padrão do Orion Context Broker na VM (para /v2/entities)

FIWARE_SERVICE = 'smart'
FIWARE_SERVICE_PATH = '/'

NEXUSCODE_DEVICE_ID = "urn:ngsi-ld:NEXUScode:003"
NEXUSCODE_ENTITY_TYPE = "Acess"

# Atributos que você quer exibir no dashboard
# NOTA: 'state' é único, os outros são logs/contadores
ATTRIBUTES_FOR_SUMMARY = ['permitido', 'negado', 'aberto', 'fechado']
ATTRIBUTES_FOR_LOG = ['permitido', 'negado', 'aberto', 'fechado', 'state'] # Inclui 'state' para o log também

LASTN_LOG_ENTRIES = 20 # Quantidade de entradas a buscar para a tabela de log

# Headers para as requisições ao FIWARE
FIWARE_HEADERS = {
    'fiware-service': FIWARE_SERVICE,
    'fiware-servicepath': FIWARE_SERVICE_PATH
}

# Configura fuso horário de São Paulo
SAO_PAULO_TZ = pytz.timezone('America/Sao_Paulo')

# --- Funções de Coleta de Dados do FIWARE ---

def get_current_entity_state():
    """Busca o estado atual da entidade NEXUScode3 do Orion Context Broker."""
    url = f"http://{VM_IP_ADDRESS}:{PORT_ORION}/v2/entities/{NEXUSCODE_DEVICE_ID}?type={NEXUSCODE_ENTITY_TYPE}"
    headers = {
        **FIWARE_HEADERS, # Adiciona os headers Fiware
        'Accept': 'application/json'
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter estado atual da entidade do Orion: {e}")
        return {}

def get_historical_data_for_attribute(attribute_name, lastN):
    """Busca o histórico de um atributo específico do STH-Comet."""
    url = f"http://{VM_IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/{NEXUSCODE_ENTITY_TYPE}/id/{NEXUSCODE_DEVICE_ID}/attributes/{attribute_name}?lastN={lastN}"
    try:
        response = requests.get(url, headers=FIWARE_HEADERS, timeout=10)
        response.raise_for_status()
        json_data = response.json()
        
        values = []
        if 'contextResponses' in json_data and json_data['contextResponses']:
            context_element = json_data['contextResponses'][0]['contextElement']
            if 'attributes' in context_element and context_element['attributes']:
                attribute_data = context_element['attributes'][0]
                if 'values' in attribute_data and attribute_data['values']:
                    values = attribute_data['values']
        return values
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar Fiware STH-Comet para histórico de {attribute_name}: {e}")
    return []

def convert_utc_to_sao_paulo(timestamp_str):
    """Converte timestamp UTC (ISO 8601) para o fuso horário de São Paulo."""
    try:
        # Tenta analisar com microssegundos, se falhar, tenta sem
        try:
            dt_object_utc = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            dt_object_utc = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')
            
        utc_dt = pytz.utc.localize(dt_object_utc)
        sao_paulo_dt = utc_dt.astimezone(SAO_PAULO_TZ)
        return sao_paulo_dt.strftime('%d/%m/%Y %H:%M:%S')
    except Exception as e:
        print(f"Erro ao converter timestamp '{timestamp_str}': {e}")
        return timestamp_str # Retorna original se houver erro

# --- Criação do App Flask e Dash ---
server = Flask(__name__)

app = dash.Dash(__name__, server=server, url_base_pathname="/dashboard/", 
                 external_stylesheets=[dbc.themes.BOOTSTRAP]) # Adiciona estilo Bootstrap

app.title = "NEXUScode3 Dashboard"

# Layout do Dashboard
app.layout = dbc.Container([
    html.H1("Dashboard - NEXUScode3", className="text-center my-4"),

    dcc.Interval(id="interval-component", interval=5000, n_intervals=0), # Atualiza a cada 5 segundos

    # Cards para o estado atual e métricas de resumo
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Estado Atual do Dispositivo"),
                dbc.CardBody([
                    html.H4(id="estado-card-title", className="card-title text-center"),
                    html.P("Última atualização:", className="card-text text-muted text-center", style={"font-size": "0.9em"}),
                    html.P(id="timestamp-card", className="card-text text-muted text-center", style={"font-size": "0.9em"})
                ])
            ], color="primary", outline=True, className="text-white bg-primary text-center m-2"),
            md=12
        )
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Acessos Permitidos"),
                dbc.CardBody(html.H3(id="permitido-card", className="card-title text-center"))
            ], color="success", outline=True, className="text-center m-2"),
            md=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Acessos Negados"),
                dbc.CardBody(html.H3(id="negado-card", className="card-title text-center"))
            ], color="danger", outline=True, className="text-center m-2"),
            md=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Contagem de Aberturas"),
                dbc.CardBody(html.H3(id="aberto-card", className="card-title text-center"))
            ], color="info", outline=True, className="text-center m-2"),
            md=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Contagem de Fechamentos"),
                dbc.CardBody(html.H3(id="fechado-card", className="card-title text-center"))
            ], color="warning", outline=True, className="text-center m-2"),
            md=3
        )
    ], className="mb-4"),

    html.Hr(),

    html.H2("Histórico de Eventos", className="text-center my-4"),
    dbc.Row([
        dbc.Col(
            # Tabela para exibir o histórico de eventos
            dash_table.DataTable(
                id='event-log-table',
                columns=[
                    {"name": "Horário (São Paulo)", "id": "timestamp_sp"},
                    {"name": "Atributo", "id": "attribute_name"},
                    {"name": "Valor", "id": "attribute_value"}
                ],
                data=[], # Dados serão preenchidos pelo callback
                style_table={'overflowX': 'auto', 'margin-bottom': '20px'},
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_cell={'textAlign': 'center'},
                page_action='native', # Habilita paginação nativa
                page_size=10, # 10 linhas por página
                sort_action='native', # Habilita ordenação nativa
                filter_action='native', # Habilita filtros nativos
            ),
            md=12
        )
    ])
], fluid=True) # fluid=True para ocupar toda a largura da tela

# Callback para atualizar o dashboard
@app.callback(
    [Output("estado-card-title", "children"),
     Output("permitido-card", "children"),
     Output("negado-card", "children"),
     Output("aberto-card", "children"),
     Output("fechado-card", "children"),
     Output("timestamp-card", "children"),
     Output("event-log-table", "data")], # Saída para os dados da tabela
    [Input("interval-component", "n_intervals")]
)
def update_dashboard(n):
    current_time_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    # 1. Obter o estado atual da entidade (do Orion)
    current_state_data = get_current_entity_state()
    state = current_state_data.get('state', {}).get('value', 'Indefinido')
    
    # Obter os valores atuais para os cards de resumo (assumindo que são do Orion agora)
    permitido_current = current_state_data.get('permitido', {}).get('value', 'N/A')
    negado_current = current_state_data.get('negado', {}).get('value', 'N/A')
    aberto_current = current_state_data.get('aberto', {}).get('value', 'N/A')
    fechado_current = current_state_data.get('fechado', {}).get('value', 'N/A')

    # 2. Obter o histórico de eventos (do STH-Comet)
    all_log_entries = []
    for attr in ATTRIBUTES_FOR_LOG:
        historical_values = get_historical_data_for_attribute(attr, LASTN_LOG_ENTRIES)
        for entry in historical_values:
            all_log_entries.append({
                'timestamp_utc': entry.get('recvTime', ''),
                'timestamp_sp': convert_utc_to_sao_paulo(entry.get('recvTime', '')),
                'attribute_name': attr.capitalize(), # Capitaliza para exibição
                'attribute_value': entry.get('attrValue', 'N/A')
            })
    
    # Ordenar todas as entradas de log pela data mais recente (decrescente)
    # Primeiro, converte 'recvTime' para datetime objects para ordenação correta
    # e trata os casos onde 'recvTime' pode estar vazio ou mal formatado.
    def sort_key(item):
        try:
            # Tenta analisar com microssegundos, se falhar, tenta sem
            try:
                return datetime.datetime.strptime(item.get('timestamp_utc', '1970-01-01T00:00:00.000Z'), '%Y-%m-%dT%H:%M:%S.%fZ')
            except ValueError:
                return datetime.datetime.strptime(item.get('timestamp_utc', '1970-01-01T00:00:00Z'), '%Y-%m-%dT%H:%M:%SZ')
        except Exception:
            return datetime.datetime(1970, 1, 1) # Retorna uma data antiga para itens mal formatados
            
    all_log_entries.sort(key=sort_key, reverse=True)
    
    # Pega apenas as LASTN_LOG_ENTRIES mais recentes para a tabela
    table_data = all_log_entries[:LASTN_LOG_ENTRIES]

    return (
        f"Estado: {state}",
        permitido_current,
        negado_current,
        aberto_current,
        fechado_current,
        f"Atualizado em: {current_time_str}",
        table_data
    )

# Inicia o servidor Flask na porta 5000, na sua máquina local.
if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5000)