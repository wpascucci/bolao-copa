import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURAÇÃO DA PÁGINA (Deve ser a primeira linha) ---
st.set_page_config(page_title="Bolão Copa 2026", page_icon="🏆", layout="centered")

# --- CUSTOM CSS PARA MELHORAR A UX ---
st.markdown("""
    <style>
    .stButton>button {
        border-radius: 20px;
        font-weight: bold;
    }
    .placar-box {
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM FIREBASE ---
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            firebase_creds = json.loads(st.secrets["firebase_credentials"])
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred)
        except Exception:
            return None
    return firestore.client()

db = init_firebase()

# --- DADOS REAIS DA COPA 2026 ---
GRUPOS_2026 = {
    "A": ["México (MEX)", "África do Sul (RSA)", "Coreia do Sul (KOR)", "República Tcheca (CZE)"],
    "B": ["Canadá (CAN)", "Bósnia e Herze. (BIH)", "Catar (QAT)", "Suíça (SUI)"],
    "C": ["Brasil (BRA)", "Marrocos (MAR)", "Haiti (HAI)", "Escócia (SCO)"],
    "D": ["Estados Unidos (USA)", "Paraguai (PAR)", "Austrália (AUS)", "Turquia (TUR)"],
    "E": ["Alemanha (GER)", "Curaçao (CUW)", "Costa do Marfim (CIV)", "Equador (ECU)"],
    "F": ["Holanda (NED)", "Japão (JPN)", "Suécia (SWE)", "Tunísia (TUN)"],
    "G": ["Bélgica (BEL)", "Egito (EGY)", "Irã (IRN)", "Nova Zelândia (NZL)"],
    "H": ["Espanha (ESP)", "Cabo Verde (CPV)", "Arábia Saudita (KSA)", "Uruguai (URU)"],
    "I": ["França (FRA)", "Senegal (SEN)", "Iraque (IRQ)", "Noruega (NOR)"],
    "J": ["Argentina (ARG)", "Argélia (ALG)", "Áustria (AUT)", "Jordânia (JOR)"],
    "K": ["Portugal (POR)", "RD Congo (COD)", "Uzbequistão (UZB)", "Colômbia (COL)"],
    "L": ["Inglaterra (ENG)", "Croácia (CRO)", "Gana (GHA)", "Panamá (PAN)"]
}

# Gerador automático da tabela (Fase de Grupos)
def gerar_tabela():
    jogos = []
    id_jogo = 1
    for grupo, times in GRUPOS_2026.items():
        # Rodada 1
        jogos.append({"id": f"g{grupo}_{id_jogo}", "grupo": grupo, "rodada": 1, "time_a": times[0], "time_b": times[1]})
        jogos.append({"id": f"g{grupo}_{id_jogo+1}", "grupo": grupo, "rodada": 1, "time_a": times[2], "time_b": times[3]})
        # Rodada 2
        jogos.append({"id": f"g{grupo}_{id_jogo+2}", "grupo": grupo, "rodada": 2, "time_a": times[0], "time_b": times[2]})
        jogos.append({"id": f"g{grupo}_{id_jogo+3}", "grupo": grupo, "rodada": 2, "time_a": times[3], "time_b": times[1]})
        # Rodada 3
        jogos.append({"id": f"g{grupo}_{id_jogo+4}", "grupo": grupo, "rodada": 3, "time_a": times[3], "time_b": times[0]})
        jogos.append({"id": f"g{grupo}_{id_jogo+5}", "grupo": grupo, "rodada": 3, "time_a": times[1], "time_b": times[2]})
        id_jogo += 6
    return jogos

JOGOS = gerar_tabela()

# --- GERENCIAMENTO DE ESTADO ---
if "jogo_selecionado" not in st.session_state:
    st.session_state.jogo_selecionado = None

# --- SIDEBAR (MENU DE NAVEGAÇÃO) ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/2026_FIFA_World_Cup_logo.svg/800px-2026_FIFA_World_Cup_logo.svg.png", width=150)
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Ir para:", ["Tabela de Jogos", "Painel do Admin (Resultados)"])

# --- TELA 1: TABELA COMPLETA DA COPA ---
if menu == "Tabela de Jogos":
    st.title("📅 Tabela da Copa 2026")
    st.write("Acompanhe todos os jogos da fase de grupos.")
    
    # Criando 12 abas, uma para cada grupo
    abas = st.tabs([f"Grupo {g}" for g in GRUPOS_2026.keys()])
    
    for i, (grupo, times) in enumerate(GRUPOS_2026.items()):
        with abas[i]:
            st.subheader(f"Seleções do Grupo {grupo}")
            st.write(" • ".join([t.split(" (")[0] for t in times]))
            st.divider()
            
            jogos_grupo = [j for j in JOGOS if j["grupo"] == grupo]
            for rodada in [1, 2, 3]:
                st.markdown(f"**{rodada}ª Rodada**")
                jogos_rodada = [j for j in jogos_grupo if j["rodada"] == rodada]
                
                for jogo in jogos_rodada:
                    # Card Visual do Jogo
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1, 3])
                        with c1:
                            st.markdown(f"<div style='text-align: right; font-size: 18px;'>{jogo['time_a']}</div>", unsafe_allow_html=True)
                        with c2:
                            st.markdown("<div style='text-align: center; color: gray;'> X </div>", unsafe_allow_html=True)
                        with c3:
                            st.markdown(f"<div style='text-align: left; font-size: 18px;'>{jogo['time_b']}</div>", unsafe_allow_html=True)

# --- TELA 2: PAINEL ADMINISTRATIVO (LANÇAR RESULTADOS E ARTILHEIROS) ---
elif menu == "Painel do Admin (Resultados)":
    
    if st.session_state.jogo_selecionado is None:
        st.title("⚙️ Lançamento de Resultados")
        st.write("Selecione a partida para inserir o placar final e os autores dos gols.")
        
        # Filtro por Grupo para facilitar achar o jogo
        grupo_filtro = st.selectbox("Filtrar por Grupo:", list(GRUPOS_2026.keys()))
        jogos_filtrados = [j for j in JOGOS if j["grupo"] == grupo_filtro]
        
        for jogo in jogos_filtrados:
            with st.container(border=True):
                col_info, col_btn = st.columns([3, 1])
                with col_info:
                    st.markdown(f"**Rodada {jogo['rodada']}** | {jogo['time_a']} x {jogo['time_b']}")
                with col_btn:
                    if st.button("Lançar Placar", key=jogo['id'], use_container_width=True):
                        st.session_state.jogo_selecionado = jogo
                        st.rerun()
                        
    else:
        # TELA DE INSERÇÃO DO JOGO ESPECÍFICO
        jogo = st.session_state.jogo_selecionado
        
        if st.button("⬅ Voltar para a lista de jogos"):
            st.session_state.jogo_selecionado = None
            st.rerun()
            
        st.title("Registrar Placar Oficial")
        st.caption(f"Grupo {jogo['grupo']} • Rodada {jogo['rodada']}")
        
        with st.container(border=True):
            # 1. Linha do Placar
            col_a, col_x, col_b = st.columns([2, 1, 2])
            with col_a:
                st.markdown(f"<div class='placar-box'>{jogo['time_a']}</div>", unsafe_allow_html=True)
                gols_a = st.number_input(f"Gols marcados", min_value=0, step=1, key="ga")
            with col_x:
                st.markdown("<h1 style='text-align: center; margin-top: 30px;'>X</h1>", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"<div class='placar-box'>{jogo['time_b']}</div>", unsafe_allow_html=True)
                gols_b = st.number_input(f"Gols marcados", min_value=0, step=1, key="gb")

        st.subheader("👟 Autores dos Gols")
        
        artilheiros_a = []
        artilheiros_b = []

        col_art_a, col_art_b = st.columns(2)
        
        with col_art_a:
            if gols_a == 0:
                st.info("Nenhum gol.")
            for i in range(gols_a):
                nome = st.text_input(f"Autor do {i+1}º gol ({jogo['time_a'].split(' ')[0]})", key=f"art_a_{i}")
                if nome:
                    artilheiros_a.append(nome)

        with col_art_b:
            if gols_b == 0:
                st.info("Nenhum gol.")
            for i in range(gols_b):
                nome = st.text_input(f"Autor do {i+1}º gol ({jogo['time_b'].split(' ')[0]})", key=f"art_b_{i}")
                if nome:
                    artilheiros_b.append(nome)

        st.divider()
        
        if st.button("💾 Salvar Resultado Definitivo", type="primary", use_container_width=True):
            if len(artilheiros_a) != gols_a or len(artilheiros_b) != gols_b:
                st.error("⚠️ Atenção: O número de artilheiros preenchidos deve ser igual ao número de gols.")
            else:
                dados_oficiais = {
                    "id_partida": jogo['id'],
                    "placar": {jogo['time_a']: gols_a, jogo['time_b']: gols_b},
                    "artilheiros": {jogo['time_a']: artilheiros_a, jogo['time_b']: artilheiros_b}
                }
                
                if db:
                    db.collection("resultados_oficiais").document(jogo['id']).set(dados_oficiais)
                    st.success("✅ Resultado salvo com sucesso no banco de dados!")
                else:
                    st.success("✅ Resultado registrado (Modo Local/Demonstração).")
                    
                # Limpar estado para voltar
                st.session_state.jogo_selecionado = None
