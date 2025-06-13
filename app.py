from flask import Flask
import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output
import datetime
import requests
import pytz
import pandas as pd
import dash_bootstrap_components as dbc

# --- Configurações da VM e FIWARE ---
VM_IP_ADDRESS = "130.131.16.56" # CONFIRMADO ESTE IP!
PORT_STH = 8666
PORT_ORION = 1026

FIWARE_SERVICE = 'smart'
FIWARE_SERVICE_PATH = '/'

NEXUSCODE_DEVICE_ID = "urn:ngsi-ld:NEXUScode:003"
NEXUSCODE_ENTITY_TYPE = "Acess"

# Mapeamento de IDs para Nomes
ID_TO_NAME_MAP = {
    "B3 9A 3A DA": "Matheus Eiki",
    "D3 16 CF 9A": "Ana Paula",
    "4D 2E AB 10": "Carlos Pereira",
    "BA AD DF 86": "Beatriz Lima",
    "46 A2 8A 3F": "Fernando Costa",
    "D2 DD 56 1B": "Gabriela Souza"
    # Adicione mais IDs e nomes aqui conforme necessário
}

# Atributos que você quer exibir no dashboard
ATTRIBUTES_FOR_SUMMARY_IDS = ['permitido', 'negado']
ATTRIBUTES_FOR_SUMMARY_COUNTS = ['aberto', 'fechado']

ATTRIBUTES_FOR_LOG = ['permitido', 'negado', 'aberto', 'fechado', 'state']

# AJUSTADO PARA O LIMITE DO SEU FIWARE (100)
LASTN_LOG_ENTRIES = 100
LASTN_FOR_SUMMARY_COUNTS = 100

FIWARE_HEADERS = {
    'fiware-service': FIWARE_SERVICE,
    'fiware-servicepath': FIWARE_SERVICE_PATH
}

SAO_PAULO_TZ = pytz.timezone('America/Sao_Paulo')

# --- Funções de Coleta de Dados do FIWARE ---

def get_current_entity_state():
    """Busca o estado atual da entidade NEXUScode3 do Orion Context Broker."""
    url = f"http://{VM_IP_ADDRESS}:{PORT_ORION}/v2/entities/{NEXUSCODE_DEVICE_ID}?type={NEXUSCODE_ENTITY_TYPE}"
    headers = {
        **FIWARE_HEADERS,
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
    if not timestamp_str:
        return "N/A"
    try:
        try:
            dt_object_utc = datetime.datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            dt_object_utc = datetime.datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ')
            
        utc_dt = pytz.utc.localize(dt_object_utc)
        sao_paulo_dt = utc_dt.astimezone(SAO_PAULO_TZ)
        return sao_paulo_dt.strftime('%d/%m/%Y %H:%M:%S')
    except Exception as e:
        print(f"Erro ao converter timestamp '{timestamp_str}': {e}")
        return timestamp_str

# --- Criação do App Flask e Dash ---
server = Flask(__name__)

app = dash.Dash(__name__, server=server, url_base_pathname="/dashboard/",
                external_stylesheets=[dbc.themes.BOOTSTRAP])

app.title = "NEXUScode3 Dashboard"

# Layout do Dashboard
app.layout = dbc.Container([
    html.H1("SmartFlow - Carrinho 3", className="text-center my-4"),

    dcc.Interval(id="interval-component", interval=10000, n_intervals=0),

    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Estado Atual do Dispositivo"),
                dbc.CardBody([
                    # Texto do estado será branco devido a `text-white`
                    html.H4(id="estado-card-title", className="card-title text-center text-white"),
                    html.P("Última atualização:", className="card-text text-center text-white", style={"font-size": "0.9em"}),
                    html.P(id="timestamp-card", className="card-text text-center text-white", style={"font-size": "0.9em"})
                ])
            ], color="primary", inverse=True, className="text-center m-2 shadow"), # `inverse=True` já faz o texto branco
            md=12
        )
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Último Acesso permitido"),
                dbc.CardBody(html.H3(id="permitido-card", className="card-title text-center"))
            ], color="success", outline=True, className="text-center m-2 shadow"),
            md=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Último Acesso Negado"),
                dbc.CardBody(html.H3(id="negado-card", className="card-title text-center"))
            ], color="danger", outline=True, className="text-center m-2 shadow"),
            md=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Contagem de Aberturas"),
                dbc.CardBody(html.H3(id="aberto-card", className="card-title text-center"))
            ], color="info", outline=True, className="text-center m-2 shadow"),
            md=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Contagem de Fechamentos"),
                dbc.CardBody(html.H3(id="fechado-card", className="card-title text-center"))
            ], color="warning", outline=True, className="text-center m-2 shadow"),
            md=3
        )
    ], className="mb-4"),

    html.Hr(),

    html.H2("Histórico de Eventos", className="text-center my-4"),
    dbc.Row([
        dbc.Col(
            dash_table.DataTable(
                id='event-log-table',
                columns=[
                    {"name": "Horário (São Paulo)", "id": "Horário (São Paulo)"},
                    {"name": "Estado", "id": "State"},
                    {"name": "Permitido", "id": "Permitido"},
                    {"name": "Negado", "id": "Negado"},
                    {"name": "Aberto", "id": "Aberto"},
                    {"name": "Fechado", "id": "Fechado"},
                ],
                data=[],
                style_table={'overflowX': 'auto', 'margin-bottom': '20px', 'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)'},
                style_header={
                    'backgroundColor': '#f8f9fa',
                    'fontWeight': 'bold',
                    'textAlign': 'center',
                    'border': '1px solid #dee2e6'
                },
                style_cell={
                    'textAlign': 'center',
                    'minWidth': '100px', 'width': '150px', 'maxWidth': '200px',
                    'fontFamily': 'Arial, sans-serif',
                    'fontSize': '14px',
                    'border': '1px solid #dee2e6'
                },
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                page_action='native',
                page_size=10,
                sort_action='native',
                filter_action='native',
            ),
            md=12
        )
    ])
], fluid=True)

# Callback para atualizar o dashboard
@app.callback(
    [Output("estado-card-title", "children"),
     Output("permitido-card", "children"),
     Output("negado-card", "children"),
     Output("aberto-card", "children"),
     Output("fechado-card", "children"),
     Output("timestamp-card", "children"),
     Output("event-log-table", "data")],
    [Input("interval-component", "n_intervals")]
)
def update_dashboard(n):
    current_time_str = datetime.datetime.now(SAO_PAULO_TZ).strftime('%d/%m/%Y %H:%M:%S')
    
    # 1. Obter o estado atual da entidade (do Orion)
    current_state_data = get_current_entity_state()
    state = current_state_data.get('state', {}).get('value', 'Indefinido')
    
    # Obter os valores atuais para os cards de resumo (que são IDs ou N/A)
    permitido_id = current_state_data.get('permitido', {}).get('value', 'N/A')
    # Mapeia ID para nome para o card "Acessos Permitidos"
    permitido_current_display = ID_TO_NAME_MAP.get(permitido_id, permitido_id)

    negado_id = current_state_data.get('negado', {}).get('value', 'N/A')
    # Mapeia ID para nome para o card "Acessos Negados"
    negado_current_display = ID_TO_NAME_MAP.get(negado_id, negado_id)
    
    # Lógica para mostrar o nome junto ao estado atual (se relevante)
    state_display = f"Estado: {state}"
    
    # Buscar os últimos eventos para tentar inferir a pessoa associada ao estado
    # Puxa os últimos N eventos de 'state', 'permitido' e 'negado'
    last_state_events = get_historical_data_for_attribute('state', 1)
    last_permitido_events = get_historical_data_for_attribute('permitido', 1)
    last_negado_events = get_historical_data_for_attribute('negado', 1)

    latest_person_id = None
    latest_person_time = datetime.datetime.min.replace(tzinfo=pytz.utc)

    # Verifica o último permitido
    if last_permitido_events:
        try:
            p_time_str = last_permitido_events[0].get('recvTime', '')
            p_time = datetime.datetime.strptime(p_time_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.utc)
            if p_time > latest_person_time:
                latest_person_time = p_time
                latest_person_id = last_permitido_events[0].get('attrValue', '')
        except ValueError: # Fallback for different timestamp format
            try:
                p_time_str = last_permitido_events[0].get('recvTime', '')
                p_time = datetime.datetime.strptime(p_time_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
                if p_time > latest_person_time:
                    latest_person_time = p_time
                    latest_person_id = last_permitido_events[0].get('attrValue', '')
            except ValueError:
                pass


    # Verifica o último negado (se for mais recente)
    if last_negado_events:
        try:
            n_time_str = last_negado_events[0].get('recvTime', '')
            n_time = datetime.datetime.strptime(n_time_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.utc)
            if n_time > latest_person_time:
                latest_person_time = n_time
                latest_person_id = last_negado_events[0].get('attrValue', '')
        except ValueError: # Fallback for different timestamp format
            try:
                n_time_str = last_negado_events[0].get('recvTime', '')
                n_time = datetime.datetime.strptime(n_time_str, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=pytz.utc)
                if n_time > latest_person_time:
                    latest_person_time = n_time
                    latest_person_id = last_negado_events[0].get('attrValue', '')
            except ValueError:
                pass

    
    # Se encontramos um ID de pessoa recente, e o estado é "aberto" ou "fechado"
    if latest_person_id and (state == "aberto" or state == "fechado"):
        person_name = ID_TO_NAME_MAP.get(latest_person_id, latest_person_id)
        state_display = f"Estado: {state} (por {person_name})"


    # 2. Obter o histórico de eventos para a tabela e contagens
    all_raw_log_entries = []
    for attr in ATTRIBUTES_FOR_LOG:
        historical_values = get_historical_data_for_attribute(attr, LASTN_LOG_ENTRIES)
        for entry in historical_values:
            all_raw_log_entries.append({
                'timestamp_utc': entry.get('recvTime', ''),
                'attribute_name': attr,
                'attribute_value': entry.get('attrValue', 'N/A') # Garante N/A para valores nulos/vazios
            })
    
    # Organizar os dados brutos em um dicionário agrupado por timestamp para a tabela
    grouped_by_timestamp = {}
    for entry in all_raw_log_entries:
        ts_sp = convert_utc_to_sao_paulo(entry['timestamp_utc'])
        
        if ts_sp not in grouped_by_timestamp:
            grouped_by_timestamp[ts_sp] = {
                "Horário (São Paulo)": ts_sp,
                "State": "N/A", # Inicializa com N/A
                "Permitido": "N/A", # Inicializa com N/A
                "Negado": "N/A", # Inicializa com N/A
                "Aberto": "N/A", # Inicializa com N/A
                "Fechado": "N/A" # Inicializa com N/A
            }
        
        attr_original_name = entry['attribute_name']
        attr_value = entry['attribute_value']

        if attr_original_name == 'state':
            grouped_by_timestamp[ts_sp]["State"] = attr_value
        elif attr_original_name == 'permitido':
            grouped_by_timestamp[ts_sp]["Permitido"] = ID_TO_NAME_MAP.get(attr_value, attr_value) # Mapeia ID para nome na tabela
        elif attr_original_name == 'negado':
            grouped_by_timestamp[ts_sp]["Negado"] = ID_TO_NAME_MAP.get(attr_value, attr_value) # Mapeia ID para nome na tabela
        elif attr_original_name == 'aberto':
            grouped_by_timestamp[ts_sp]["Aberto"] = attr_value
        elif attr_original_name == 'fechado':
            grouped_by_timestamp[ts_sp]["Fechado"] = attr_value

    # Converte o dicionário agrupado para uma lista de dicionários para a dash_table
    table_data = list(grouped_by_timestamp.values())
    
    # Ordena a tabela por horário (mais recente primeiro)
    table_data.sort(key=lambda x: datetime.datetime.strptime(x['Horário (São Paulo)'], '%d/%m/%Y %H:%M:%S') if x['Horário (São Paulo)'] != "N/A" else datetime.datetime.min, reverse=True)
    
    # Contagens para os cards de "Aberturas" e "Fechamentos"
    aberto_count = len(get_historical_data_for_attribute('aberto', LASTN_FOR_SUMMARY_COUNTS))
    fechado_count = len(get_historical_data_for_attribute('fechado', LASTN_FOR_SUMMARY_COUNTS))

    return (
        state_display, # Agora inclui o nome da pessoa, se aplicável
        permitido_current_display,
        negado_current_display,
        aberto_count,
        fechado_count,
        f"Atualizado em: {current_time_str}",
        table_data
    )

if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5000)