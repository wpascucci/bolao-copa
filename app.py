import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Bolão Copa 2026", page_icon="🏆", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .locked-box { background-color: #e8f0fe; padding: 15px; border-radius: 10px; border-left: 5px solid #1a73e8; margin-bottom: 15px;}
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM FIREBASE ---
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            firebase_creds = json.loads(st.secrets["firebase_credentials"])
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception:
        return None

db = init_firebase()

# --- ESTRUTURA DA COPA 2026 (Exemplo reduzido para o motor funcionar) ---
FASES_COPA = ["Grupos", "16 Avos", "Oitavas", "Quartas", "Semifinal", "Final"]

JOGOS = [
    # Fase de Grupos (Exemplo Grupo A e B)
    {"id": "jogo_1", "fase": "Grupos", "time_a": "México", "time_b": "África do Sul"},
    {"id": "jogo_2", "fase": "Grupos", "time_a": "Brasil", "time_b": "Marrocos"},
    # 16 Avos de Final (Exemplo de cruzamento)
    {"id": "jogo_73", "fase": "16 Avos", "time_a": "1º Grupo A", "time_b": "3º Grupo C/D/E"},
    # Oitavas de final, etc...
    {"id": "jogo_89", "fase": "Oitavas", "time_a": "Vencedor Jogo 73", "time_b": "Vencedor Jogo 74"}
]

# --- CONTROLE DE SESSÃO (LOGIN) ---
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# --- TELA DE LOGIN ---
def tela_login():
    st.title("⚽ Bolão Copa do Mundo 2026")
    st.write("Faça login para registrar seus palpites.")
    
    with st.container(border=True):
        st.subheader("Acesso")
        usuario = st.text_input("Nome de Usuário (Crie um ou digite o seu)").strip().lower()
        senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar", use_container_width=True):
            if usuario == "admin" and senha == "admin123": # Troque a senha do admin depois!
                st.session_state.usuario_logado = "Admin Master"
                st.session_state.is_admin = True
                st.rerun()
            elif usuario and senha:
                # Login simples para usuários (num app real, você validaria a senha no banco)
                st.session_state.usuario_logado = usuario
                st.session_state.is_admin = False
                st.rerun()
            else:
                st.error("Preencha usuário e senha.")

# --- MOTOR DE INTERFACE DE JOGO ---
def renderizar_jogo(jogo, usuario, modo_admin=False):
    st.markdown(f"**{jogo['time_a']} x {jogo['time_b']}**")
    
    # Define onde buscar/salvar os dados (Admin salva em resultados, Usuário em palpites)
    colecao = "resultados_oficiais" if modo_admin else "palpites"
    doc_id = f"{jogo['id']}" if modo_admin else f"{usuario}_{jogo['id']}"
    
    doc_ref = db.collection(colecao).document(doc_id) if db else None
    dados_existentes = doc_ref.get().to_dict() if (doc_ref and doc_ref.get().exists) else None

    # Se já tem palpite salvo e não for o admin sobrescrevendo
    if dados_existentes and not modo_admin:
        st.markdown(f"""
        <div class="locked-box">
            <b>🔒 Palpite Confirmado!</b><br>
            Placar: {jogo['time_a']} {dados_existentes['placar_a']} x {dados_existentes['placar_b']} {jogo['time_b']}<br>
            <i>Este palpite não pode mais ser alterado.</i>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        return

    # Se não tem palpite, mostra o formulário
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    with col2:
        gols_a = st.number_input("", min_value=0, step=1, key=f"ga_{jogo['id']}_{modo_admin}", label_visibility="collapsed")
    with col3:
        gols_b = st.number_input("", min_value=0, step=1, key=f"gb_{jogo['id']}_{modo_admin}", label_visibility="collapsed")
    
    # Campo dinâmico para artilheiros
    artilheiros_a = []
    artilheiros_b = []
    
    if gols_a > 0 or gols_b > 0:
        c_art_a, c_art_b = st.columns(2)
        with c_art_a:
            for i in range(gols_a):
                artilheiros_a.append(st.text_input(f"Gol {i+1} ({jogo['time_a']})", key=f"arta_{jogo['id']}_{i}_{modo_admin}"))
        with c_art_b:
            for i in range(gols_b):
                artilheiros_b.append(st.text_input(f"Gol {i+1} ({jogo['time_b']})", key=f"artb_{jogo['id']}_{i}_{modo_admin}"))

    texto_botao = "💾 Salvar Resultado Oficial" if modo_admin else "✅ Confirmar Palpite (Irreversível)"
    
    if st.button(texto_botao, key=f"btn_{jogo['id']}_{modo_admin}"):
        if (gols_a > 0 and "" in artilheiros_a) or (gols_b > 0 and "" in artilheiros_b):
            st.error("Preencha o nome de todos os artilheiros!")
        else:
            dados = {
                "placar_a": gols_a,
                "placar_b": gols_b,
                "artilheiros_a": artilheiros_a,
                "artilheiros_b": artilheiros_b,
                "usuario": usuario
            }
            if db:
                doc_ref.set(dados)
                st.success("Salvo com sucesso!")
                st.rerun()
            else:
                st.warning("Modo demonstração: Conecte o Firebase para salvar.")
    st.divider()

# --- APLICATIVO PRINCIPAL ---
if st.session_state.usuario_logado is None:
    tela_login()
else:
    # Top bar
    col_user, col_logout = st.columns([4, 1])
    col_user.write(f"👤 Logado como: **{st.session_state.usuario_logado}**")
    if col_logout.button("Sair"):
        st.session_state.usuario_logado = None
        st.session_state.is_admin = False
        st.rerun()

    st.title("🏆 Simulador Copa 2026")

    # Separar visualização por abas baseada na fase do torneio
    abas = st.tabs(FASES_COPA + (["⚙️ ADMIN"] if st.session_state.is_admin else []))

    # Renderiza os jogos para os usuários normais dentro de cada aba
    for i, fase in enumerate(FASES_COPA):
        with abas[i]:
            st.subheader(f"Partidas - {fase}")
            jogos_da_fase = [j for j in JOGOS if j["fase"] == fase]
            
            for jogo in jogos_da_fase:
                renderizar_jogo(jogo, st.session_state.usuario_logado, modo_admin=False)

    # Renderiza a aba de Admin (Somente para admin)
    if st.session_state.is_admin:
        with abas[-1]:
            st.subheader("Área Restrita - Lançar Resultados Oficiais")
            st.info("O que for salvo aqui será a base para calcular a pontuação de todos os jogadores.")
            
            fase_selecionada = st.selectbox("Filtrar fase:", FASES_COPA)
            jogos_admin = [j for j in JOGOS if j["fase"] == fase_selecionada]
            
            for jogo in jogos_admin:
                renderizar_jogo(jogo, "admin", modo_admin=True)
