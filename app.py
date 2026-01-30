import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import ssl
import random
import socket

# --- SEUS DADOS ---
MQTT_BROKER = "a15a109cb36c4a1599f7c5bf4349f1f7.s1.eu.hivemq.cloud"
# MUDANÇA 1: Porta de Websockets (Mais amigável pro Windows)
MQTT_PORT = 8884 
MQTT_USER = "esp32_loja"
MQTT_PASSWORD = "JJunco@2026" 
TOPIC = "loja/radar1"

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Monitor Varejo", layout="wide")
st.title("📡 Monitoramento de Fluxo - Tempo Real")

# Áreas de Texto
col1, col2 = st.columns(2)
status_box = col1.empty()
log_area = col2.empty()
debug_logs = []

# --- FUNÇÃO DE LOG ---
def on_log(client, userdata, level, buf):
    debug_logs.append(f"LOG: {buf}")
    # Mostra apenas os últimos 3 logs
    log_area.code("\n".join(debug_logs[-3:]))

def on_connect(client, userdata, flags, rc):
    # O Paho v1.6.1 retorna apenas esses argumentos
    msgs = {
        0: "✅ SUCESSO! CONECTADO!",
        1: "❌ Erro Protocolo",
        3: "❌ Servidor Indisponível",
        4: "❌ Senha/Usuário Errados",
        5: "❌ Não Autorizado"
    }
    status = msgs.get(rc, f"Código: {rc}")
    st.session_state['conn_status'] = status
    if rc == 0:
        client.subscribe(TOPIC)

def on_message(client, userdata, message):
    try:
        payload = message.payload.decode("utf-8")
        dados = json.loads(payload)
        st.session_state['last_x'] = dados['x']
        st.session_state['last_y'] = dados['y']
    except:
        pass

# --- INICIALIZAÇÃO BLINDADA (WEBSOCKETS) ---
@st.cache_resource
def iniciar_mqtt():
    client_id = f"dashboard-{random.randint(0, 10000)}"
    
    # MUDANÇA 2: Usando Websockets (Passa pelo Firewall)
    client = mqtt.Client(client_id, transport="websockets")
    
    client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    
    # MUDANÇA 3: Caminho padrão do HiveMQ
    client.ws_set_options(path="/mqtt")
    
    # Segurança SSL (Obrigatória no HiveMQ)
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    client.tls_set_context(context)
    
    client.on_log = on_log
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        return client
    except Exception as e:
        st.error(f"ERRO CRÍTICO: {e}")
        return None

if 'conn_status' not in st.session_state: st.session_state['conn_status'] = "Tentando via Websockets..."
if 'last_x' not in st.session_state: st.session_state['last_x'] = 0
if 'last_y' not in st.session_state: st.session_state['last_y'] = 0

client = iniciar_mqtt()

# --- LOOP VISUAL ---
while True:
    status_msg = st.session_state['conn_status']
    status_box.metric("Status da Conexão", status_msg)
    
    if "SUCESSO" in status_msg:
        st.success(f"📍 CLIENTE EM: X={st.session_state['last_x']} | Y={st.session_state['last_y']}")
        # Barra de progresso para dar visual
        dist = st.session_state['last_y']
        st.progress(min(1.0, max(0.0, dist/400.0)))
    
    time.sleep(0.5)