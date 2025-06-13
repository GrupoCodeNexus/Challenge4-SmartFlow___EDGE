from flask import Flask
import dash
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output
import datetime
import requests
import pytz
import dash_bootstrap_components as dbc  # Importa componentes Bootstrap

# --- Configurações da VM e FIWARE ---
VM_IP_ADDRESS = "130.131.16.56"  # CONFIRME ESTE IP!
PORT_STH = 8666
PORT_ORION = 1026

FIWARE_SERVICE = 'smart'
FIWARE_SERVICE_PATH = '/'

NEXUSCODE_DEVICE_ID = "urn:ngsi-ld:NEXUScode:003"
NEXUSCODE_ENTITY_TYPE = "Acess"

ATTRIBUTES_FOR_SUMMARY = ['permitido', 'negado', 'aberto', 'fechado']
# Keep all attributes here to fetch them, then filter for display
ATTRIBUTES_FOR_LOG = ['permitido', 'negado', 'aberto', 'fechado', 'state']

LASTN_LOG_ENTRIES = 200 # Aumentei de volta para 200, pois 20 é muito pouco para contagens e histórico detalhado
LASTN_FOR_SUMMARY_COUNTS = 1000 # Mantido para garantir que você tenha dados suficientes para as contagens

FIWARE_HEADERS = {
    'fiware-service': FIWARE_SERVICE,
    'fiware-servicepath': FIWARE_SERVICE_PATH
}

SAO_PAULO_TZ = pytz.timezone('America/Sao_Paulo')

# --- Funções ---

from flask import Flask

import dash

from dash import html, dcc, dash_table

from dash.dependencies import Input, Output

import datetime

import requests

import pytz

import dash_bootstrap_components as dbc  # Importa componentes Bootstrap



# --- Configurações da VM e FIWARE ---

VM_IP_ADDRESS = "130.131.16.56"  # CONFIRME ESTE IP!

PORT_STH = 8666

PORT_ORION = 1026



FIWARE_SERVICE = 'smart'

FIWARE_SERVICE_PATH = '/'



NEXUSCODE_DEVICE_ID = "urn:ngsi-ld:NEXUScode:003"

NEXUSCODE_ENTITY_TYPE = "Acess"



ATTRIBUTES_FOR_SUMMARY = ['permitido', 'negado', 'aberto', 'fechado']

# Keep all attributes here to fetch them, then filter for display

ATTRIBUTES_FOR_LOG = ['permitido', 'negado', 'aberto', 'fechado', 'state']



LASTN_LOG_ENTRIES = 20



FIWARE_HEADERS = {

    'fiware-service': FIWARE_SERVICE,

    'fiware-servicepath': FIWARE_SERVICE_PATH

}



SAO_PAULO_TZ = pytz.timezone('America/Sao_Paulo')



# --- Funções ---



def get_current_entity_state():

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

# --- Flask + Dash setup ---

server = Flask(__name__)

app = dash.Dash(__name__, server=server, url_base_pathname="/dashboard/",
                external_stylesheets=[dbc.themes.BOOTSTRAP])

app.title = "NEXUScode3 Dashboard"

app.layout = dbc.Container([
    html.H1("Dashboard - NEXUScode3", className="text-center my-4"),

    dcc.Interval(id="interval-component", interval=5000, n_intervals=0),

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
            dash_table.DataTable(
                id='event-log-table',
                # Columns are now dynamic based on what we want to show
                columns=[],
                data=[],
                style_table={'overflowX': 'auto', 'margin-bottom': '20px'},
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold',
                    'textAlign': 'center'
                },
                style_cell={'textAlign': 'center'},
                page_action='native',
                page_size=10,
                sort_action='native',
                filter_action='native',
            ),
            md=12
        )
    ])
], fluid=True)

# --- Callback ---

@app.callback(
    [Output("estado-card-title", "children"),
     Output("permitido-card", "children"),
     Output("negado-card", "children"),
     Output("aberto-card", "children"),
     Output("fechado-card", "children"),
     Output("timestamp-card", "children"),
     Output("event-log-table", "data"),
     Output("event-log-table", "columns")],
    [Input("interval-component", "n_intervals")]
)
def update_dashboard(n):
    current_time_str = datetime.datetime.now(SAO_PAULO_TZ).strftime('%d/%m/%Y %H:%M:%S')

    current_state_data = get_current_entity_state()
    state = current_state_data.get('state', {}).get('value', 'Indefinido')

    permitido_current = current_state_data.get('permitido', {}).get('value', 'N/A')
    negado_current = current_state_data.get('negado', {}).get('value', 'N/A')
    aberto_current = current_state_data.get('aberto', {}).get('value', 'N/A')
    fechado_current = current_state_data.get('fechado', {}).get('value', 'N/A')

    all_log_entries = []
    for attr in ATTRIBUTES_FOR_LOG: # Use original ATTRIBUTES_FOR_LOG to fetch all data
        # Use LASTN_LOG_ENTRIES para o log, e LASTN_FOR_SUMMARY_COUNTS para as contagens nos cards
        hist_values = get_historical_data_for_attribute(attr, LASTN_LOG_ENTRIES)
        for entry in hist_values:
            ts_sp = convert_utc_to_sao_paulo(entry.get('recvTime', ''))
            attr_value = entry.get('attrValue', 'N/A')

            # Modify value for 'aberto' and 'fechado' to show '1' for count
            # Esta lógica é para o log, onde cada entrada individual é um evento
            # As contagens dos cards são feitas diretamente no len(get_historical_data_for_attribute(...))
            # if attr in ['aberto', 'fechado']: # Esta linha não é necessária aqui se o valor já é o ID
            #   attr_value = 1 

            all_log_entries.append({
                'timestamp_sp': ts_sp,
                'attribute_name': attr.capitalize(),
                'attribute_value': attr_value
            })

    # Agrupar por timestamp
    grouped = {}
    for entry in all_log_entries:
        ts = entry['timestamp_sp']
        attr = entry['attribute_name']
        val = entry['attribute_value']
        if ts not in grouped:
            grouped[ts] = {}
        grouped[ts][attr] = val

    # Converter agrupamento para lista de dicionários para a tabela
    table_data = []
    # Explicitly define the order of columns you want to see
    display_columns_order = ['Permitido', 'Negado', 'Aberto', 'Fechado', 'State']
    for ts, attrs in grouped.items():
        row = {'Horário (São Paulo)': ts}
        for attr_name in display_columns_order:
            row[attr_name] = attrs.get(attr_name, '')
        table_data.append(row)

    # Ordenar tabela por horário decrescente
    table_data.sort(key=lambda x: datetime.datetime.strptime(x['Horário (São Paulo)'], '%d/%m/%Y %H:%M:%S'), reverse=True)

    # Definir as colunas para exibir, ensuring 'Aberto' and 'Fechado' are present
    columns_for_display = [
        {"name": "Horário (São Paulo)", "id": "Horário (São Paulo)"},
        {"name": "Permitido", "id": "Permitido"},
        {"name": "Negado", "id": "Negado"},
        {"name": "Aberto", "id": "Aberto"},
        {"name": "Fechado", "id": "Fechado"},
        {"name": "State", "id": "State"}
    ]

    # As contagens para os cartões de resumo
    aberto_count = len(get_historical_data_for_attribute('aberto', LASTN_FOR_SUMMARY_COUNTS))
    fechado_count = len(get_historical_data_for_attribute('fechado', LASTN_FOR_SUMMARY_COUNTS))

    return (
        f"Estado: {state}",
        permitido_current,
        negado_current,
        aberto_count,   # Aqui é a contagem
        fechado_count,  # Aqui é a contagem
        f"Atualizado em: {current_time_str}",
        table_data,
        columns_for_display
    )

if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5000)