import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Admin Bolão 2026", page_icon="🏆", layout="centered")

# --- CONEXÃO COM FIREBASE ---
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            firebase_creds = json.loads(st.secrets["firebase_credentials"])
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            return None
    return firestore.client()

db = init_firebase()

# --- DADOS DE EXEMPLO (JOGOS DA COPA) ---
# Em um cenário real, você buscaria isso de uma API ou do próprio banco de dados
JOGOS_2026 = [
    {"id": "jogo_01", "data": "11 Junho", "fase": "Abertura", "local": "Estádio Azteca", "time_a": "MEX", "time_b": "POL", "hora": "15:00"},
    {"id": "jogo_02", "data": "13 Junho", "fase": "Fase de Grupos", "local": "MetLife Stadium", "time_a": "BRA", "time_b": "MAR", "hora": "19:00"},
    {"id": "jogo_03", "data": "13 Junho", "fase": "Fase de Grupos", "local": "Gillette Stadium", "time_a": "HAI", "time_b": "SCO", "hora": "22:00"},
    {"id": "jogo_04", "data": "14 Junho", "fase": "Fase de Grupos", "local": "NRG Stadium", "time_a": "GER", "time_b": "CUW", "hora": "14:00"},
]

# --- GERENCIAMENTO DE ESTADO ---
if "tela_atual" not in st.session_state:
    st.session_state.tela_atual = "lista_jogos"
if "jogo_selecionado" not in st.session_state:
    st.session_state.jogo_selecionado = None

# --- FUNÇÕES DE NAVEGAÇÃO ---
def ir_para_detalhe(jogo):
    st.session_state.jogo_selecionado = jogo
    st.session_state.tela_atual = "detalhe_jogo"

def voltar_para_lista():
    st.session_state.jogo_selecionado = None
    st.session_state.tela_atual = "lista_jogos"

# --- TELA 1: LISTA DE JOGOS ---
def mostrar_lista_jogos():
    st.title("Lista de Partidas")
    st.write("Selecione um jogo para lançar o placar e os artilheiros oficiais.")
    
    if db is None:
        st.warning("⚠️ Firebase não conectado. O aplicativo funcionará de forma visual, mas não salvará os dados. Configure os Secrets no Streamlit Cloud.")

    data_atual = ""
    for jogo in JOGOS_2026:
        # Agrupamento por data (visual)
        if jogo["data"] != data_atual:
            data_atual = jogo["data"]
            st.markdown(f"#### 📅 {data_atual} • {jogo['fase']}")
            st.divider()
        
        # Card do Jogo
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.caption(f"{jogo['hora']} | {jogo['local']}")
            with col2:
                st.markdown(f"<h4 style='text-align: center;'>{jogo['time_a']}  X  {jogo['time_b']}</h4>", unsafe_allow_html=True)
            with col3:
                # Botão que muda o estado da aplicação
                st.button("Lançar Resultado", key=f"btn_{jogo['id']}", on_click=ir_para_detalhe, args=(jogo,), use_container_width=True)
        st.write("") # Espaçamento

# --- TELA 2: INSERÇÃO DE DADOS DO JOGO ---
def mostrar_detalhe_jogo():
    jogo = st.session_state.jogo_selecionado
    
    st.button("⬅ Voltar", on_click=voltar_para_lista)
    
    st.title("Inserção de Dados")
    st.caption(f"{jogo['fase']} • {jogo['data']} • {jogo['local']}")
    
    # 1. Placar
    st.subheader(f"Placar Final: {jogo['time_a']} vs {jogo['time_b']}")
    col_a, col_x, col_b = st.columns([2, 1, 2])
    
    with col_a:
        gols_a = st.number_input(f"Gols do(a) {jogo['time_a']}", min_value=0, step=1, value=0)
    with col_x:
        st.markdown("<h2 style='text-align: center; margin-top: 20px;'>X</h2>", unsafe_allow_html=True)
    with col_b:
        gols_b = st.number_input(f"Gols do(a) {jogo['time_b']}", min_value=0, step=1, value=0)

    st.divider()

    # 2. Artilheiros (Campos gerados dinamicamente com base no placar numérico)
    st.subheader("Artilheiros da Partida")
    
    artilheiros_a = []
    artilheiros_b = []

    col_art_a, col_art_b = st.columns(2)
    
    with col_art_a:
        st.markdown(f"**Gols do(a) {jogo['time_a']}: {gols_a}**")
        if gols_a == 0:
            st.info("Nenhum gol marcado.")
        for i in range(gols_a):
            nome = st.text_input(f"Autor do {i+1}º gol ({jogo['time_a']})", key=f"art_a_{i}")
            if nome:
                artilheiros_a.append(nome)

    with col_art_b:
        st.markdown(f"**Gols do(a) {jogo['time_b']}: {gols_b}**")
        if gols_b == 0:
            st.info("Nenhum gol marcado.")
        for i in range(gols_b):
            nome = st.text_input(f"Autor do {i+1}º gol ({jogo['time_b']})", key=f"art_b_{i}")
            if nome:
                artilheiros_b.append(nome)

    st.divider()
    
    # 3. Botão de Salvar
    if st.button("💾 Salvar Resultado no Banco de Dados", type="primary", use_container_width=True):
        
        # Validação básica
        if len(artilheiros_a) != gols_a or len(artilheiros_b) != gols_b:
            st.error("⚠️ Atenção: Preencha o nome de todos os artilheiros antes de salvar.")
        else:
            dados_partida = {
                "id_partida": jogo['id'],
                "placar": {
                    jogo['time_a']: gols_a,
                    jogo['time_b']: gols_b
                },
                "artilheiros": {
                    jogo['time_a']: artilheiros_a,
                    jogo['time_b']: artilheiros_b
                },
                "status": "encerrada"
            }
            
            # Salvar no Firebase
            if db:
                try:
                    db.collection("partidas_encerradas").document(jogo['id']).set(dados_partida)
                    st.success("✅ Resultado salvo com sucesso no Firebase! O ranking será atualizado.")
                    # Poderia chamar a função de processar pontuações dos usuários aqui
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.success("✅ Resultado registrado (Modo Demonstração).")
                st.json(dados_partida)

# --- ROTEAMENTO (ROUTER) ---
if st.session_state.tela_atual == "lista_jogos":
    mostrar_lista_jogos()
elif st.session_state.tela_atual == "detalhe_jogo":
    mostrar_detalhe_jogo()
