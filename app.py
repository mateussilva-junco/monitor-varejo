import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import ssl
import random

# --- SEUS DADOS ---
MQTT_BROKER = "a15a109cb36c4a1599f7c5bf4349f1f7.s1.eu.hivemq.cloud"
# MUDANÇA: Porta 8884 (Websockets) - Mais robusta para nuvem
MQTT_PORT = 8884 
MQTT_USER = "esp32_loja"
MQTT_PASSWORD = "JJunco@2026" 
TOPIC = "loja/radar1"

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Monitor Varejo", layout="wide")
st.title("📡 Monitoramento de Fluxo - Tempo Real")

# --- BARRA LATERAL ---
st.sidebar.header("🔧 Status do Sistema")
status_text = st.sidebar.empty()

# --- VARIÁVEIS DE ESTADO ---
if 'last_x' not in st.session_state: st.session_state['last_x'] = 0
if 'last_y' not in st.session_state: st.session_state['last_y'] = 0
if 'conn_status' not in st.session_state: st.session_state['conn_status'] = "Iniciando..."

# --- FUNÇÕES MQTT ---
def on_message(client, userdata, message):
    try:
        payload = message.payload.decode("utf-8")
        dados = json.loads(payload)
        st.session_state['last_x'] = dados['x']
        st.session_state['last_y'] = dados['y']
    except Exception as e:
        print(f"Erro JSON: {e}")

def on_connect(client, userdata, flags, rc, properties=None):
    msgs = {
        0: "Conectado com Sucesso! 🟢",
        1: "Erro de Protocolo",
        3: "Servidor Indisponível",
        4: "Erro de Senha/Usuário 🔴",
        5: "Não Autorizado"
    }
    status = msgs.get(rc, f"Código: {rc}")
    st.session_state['conn_status'] = status
    if rc == 0:
        client.subscribe(TOPIC)

# --- CONEXÃO WEBSOCKETS (A Chave do Sucesso) ---
def conectar_mqtt():
    client_id = f"dashboard-cloud-{random.randint(0, 10000)}"
    
    # 1. Define transporte como WEBSOCKETS
    # Tenta usar a versão nova, se falhar usa a antiga
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id, transport="websockets")
    except AttributeError:
        client = mqtt.Client(client_id, transport="websockets")
    
    # 2. Configura o caminho (Obrigatório para HiveMQ)
    client.ws_set_options(path="/mqtt")
    
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    
    # 3. Segurança SSL (Obrigatório)
    client.tls_set(cert_reqs=ssl.CERT_NONE)
    client.tls_insecure_set(True)
    
    client.on_message = on_message
    client.on_connect = on_connect
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        return client
    except Exception as e:
        st.session_state['conn_status'] = f"Erro Rede: {e}"
        return None

# --- INICIA APENAS UMA VEZ ---
if 'mqtt_client_obj' not in st.session_state:
    st.session_state['mqtt_client_obj'] = conectar_mqtt()

# --- DASHBOARD VISUAL ---
col1, col2, col3 = st.columns(3)
kpi_status = col1.empty()
kpi_dist = col2.empty()
kpi_lat = col3.empty()
msg_area = st.empty()
bar_area = st.empty()

while True:
    # Atualiza Status
    status = st.session_state['conn_status']
    status_text.text(status)
    
    if "Sucesso" in status:
        kpi_status.metric("Sistema", "🟢 Online")
    elif "Erro" in status:
        kpi_status.metric("Sistema", "🔴 Falha")
    else:
        kpi_status.metric("Sistema", "🟡 Conectando...")

    # Atualiza Dados
    x = st.session_state['last_x']
    y = st.session_state['last_y']
    
    kpi_dist.metric("Profundidade", f"{y} cm")
    kpi_lat.metric("Lateral", f"{x} cm")
    
    if y > 0:
        msg_area.success(f"📍 CLIENTE EM: X={x} / Y={y}")
        progresso = 1.0 - (min(y, 400) / 400.0)
        bar_area.progress(max(0.0, progresso))
    else:
        msg_area.info("Aguardando movimento...")
        bar_area.empty()
    
    time.sleep(0.5)
