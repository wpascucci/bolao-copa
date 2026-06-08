import streamlit as st
import pandas as pd
import json
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Bolão Copa 2026", page_icon="🏆", layout="wide")

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

FASES_COPA = ["Grupos", "16 Avos", "Oitavas", "Quartas", "Semifinal", "Final"]
JOGOS = [
    {"id": "jogo_1", "fase": "Grupos", "time_a": "México", "time_b": "África do Sul"},
    {"id": "jogo_2", "fase": "Grupos", "time_a": "Brasil", "time_b": "Marrocos"}
]

# --- CONTROLE DE SESSÃO ---
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# --- LÓGICA DE PONTUAÇÃO MATEMÁTICA ---
def calcular_desempenho(palpite, oficial):
    p_a, p_b = palpite.get('placar_a', 0), palpite.get('placar_b', 0)
    o_a, o_b = oficial.get('placar_a', 0), oficial.get('placar_b', 0)
    
    pontos = 0
    stats = {"exato": 0, "vencedor": 0, "perdedor": 0, "artilheiro": 0}
    
    vencedor_p = 'A' if p_a > p_b else 'B' if p_b > p_a else 'E'
    vencedor_o = 'A' if o_a > o_b else 'B' if o_b > o_a else 'E'
    
    # 1. Placar Exato (25 pts)
    if p_a == o_a and p_b == o_b:
        pontos += 25
        stats["exato"] = 1
    else:
        # 2 e 3. Acertou Vencedor (10 pts) + Bônus Gols Vencedor (5 pts)
        if vencedor_p == vencedor_o:
            pontos += 10
            stats["vencedor"] = 1
            if (vencedor_o == 'A' and p_a == o_a) or (vencedor_o == 'B' and p_b == o_b):
                pontos += 5
                
        # 4. Acertou Placar do Perdedor (2 pts)
        if (vencedor_o == 'A' and p_b == o_b) or (vencedor_o == 'B' and p_a == o_a):
            pontos += 2
            stats["perdedor"] = 1

    # 5. Artilheiros (Bonus por acerto exato de nome - 5 pts por gol acertado)
    art_p = [a.strip().lower() for a in palpite.get('artilheiros_a', []) + palpite.get('artilheiros_b', []) if a]
    art_o = [a.strip().lower() for a in oficial.get('artilheiros_a', []) + oficial.get('artilheiros_b', []) if a]
    
    for jogador in art_p:
        if jogador in art_o:
            pontos += 5
            stats["artilheiro"] += 1
            art_o.remove(jogador) # Remove para não contar em dobro se ele fez 2 gols e o usuário só botou 1
            
    return pontos, stats

# --- TELA DE LOGIN ---
def tela_login():
    st.title("⚽ Bolão Copa do Mundo 2026")
    with st.container(border=True):
        usuario = st.text_input("Usuário").strip().lower()
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            if usuario == "admin" and senha == "admin123":
                st.session_state.usuario_logado = "Admin"
                st.session_state.is_admin = True
                st.rerun()
            elif usuario and senha:
                st.session_state.usuario_logado = usuario
                st.session_state.is_admin = False
                st.rerun()

# --- MOTOR DE INTERFACE DE JOGO ---
def renderizar_jogo(jogo, usuario, modo_admin=False):
    st.markdown(f"**{jogo['time_a']} x {jogo['time_b']}**")
    
    colecao = "resultados_oficiais" if modo_admin else "palpites"
    doc_id = f"{jogo['id']}" if modo_admin else f"{usuario}_{jogo['id']}"
    
    doc_ref = db.collection(colecao).document(doc_id) if db else None
    dados_existentes = doc_ref.get().to_dict() if (doc_ref and doc_ref.get().exists) else None

    # Bloqueio de edição para usuários normais
    if dados_existentes and not modo_admin:
        st.markdown(f"""
        <div class="locked-box">
            <b>🔒 Palpite Confirmado!</b><br>
            Placar: {jogo['time_a']} {dados_existentes['placar_a']} x {dados_existentes['placar_b']} {jogo['time_b']}
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        return

    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
    with col2:
        gols_a = st.number_input("", min_value=0, step=1, key=f"ga_{jogo['id']}_{modo_admin}", label_visibility="collapsed")
    with col3:
        gols_b = st.number_input("", min_value=0, step=1, key=f"gb_{jogo['id']}_{modo_admin}", label_visibility="collapsed")
    
    art_a, art_b = [], []
    if gols_a > 0 or gols_b > 0:
        c_art_a, c_art_b = st.columns(2)
        with c_art_a:
            for i in range(gols_a): art_a.append(st.text_input(f"Gol {i+1} ({jogo['time_a']})", key=f"aa_{jogo['id']}_{i}_{modo_admin}"))
        with c_art_b:
            for i in range(gols_b): art_b.append(st.text_input(f"Gol {i+1} ({jogo['time_b']})", key=f"ab_{jogo['id']}_{i}_{modo_admin}"))

    if st.button("💾 Salvar Resultado Oficial" if modo_admin else "✅ Confirmar Palpite", key=f"btn_{jogo['id']}_{modo_admin}"):
        if (gols_a > 0 and "" in art_a) or (gols_b > 0 and "" in art_b):
            st.error("Preencha todos os artilheiros!")
        else:
            if db:
                doc_ref.set({"placar_a": gols_a, "placar_b": gols_b, "artilheiros_a": art_a, "artilheiros_b": art_b, "usuario": usuario, "id_jogo": jogo['id']})
                st.success("Salvo com sucesso!")
                st.rerun()
    st.divider()

# --- APLICATIVO PRINCIPAL ---
if st.session_state.usuario_logado is None:
    tela_login()
else:
    c_user, c_out = st.columns([4, 1])
    c_user.write(f"👤 Logado como: **{st.session_state.usuario_logado}**")
    if c_out.button("Sair"):
        st.session_state.usuario_logado = None
        st.session_state.is_admin = False
        st.rerun()

    st.title("🏆 Simulador Copa 2026")

    # Separação estrita de visão: Admin vs Usuário
    nomes_abas = ["⚙️ ADMIN", "📊 RANKING"] if st.session_state.is_admin else FASES_COPA + ["📊 RANKING"]
    abas = st.tabs(nomes_abas)

    if st.session_state.is_admin:
        with abas[0]:
            st.subheader("Área Restrita - Lançar Resultados Oficiais")
            fase_sel = st.selectbox("Fase:", FASES_COPA)
            for jogo in [j for j in JOGOS if j["fase"] == fase_sel]:
                renderizar_jogo(jogo, "admin", modo_admin=True)
        aba_ranking = abas[1]
    else:
        for i, fase in enumerate(FASES_COPA):
            with abas[i]:
                st.subheader(f"Partidas - {fase}")
                for jogo in [j for j in JOGOS if j["fase"] == fase]:
                    renderizar_jogo(jogo, st.session_state.usuario_logado, modo_admin=False)
        aba_ranking = abas[-1]

    # --- ABA DE RANKING (Visível para todos) ---
    with aba_ranking:
        st.header("Classificação Geral")
        if st.button("🔄 Atualizar Tabela"):
            if db:
                palpites_docs = db.collection("palpites").stream()
                oficiais_docs = db.collection("resultados_oficiais").stream()
                
                oficiais = {doc.id: doc.to_dict() for doc in oficiais_docs}
                tabela = {}

                for doc in palpites_docs:
                    p = doc.to_dict()
                    user = p.get('usuario')
                    id_j = p.get('id_jogo')
                    
                    if user not in tabela:
                        tabela[user] = {"Pontuação Total": 0, "Placar Exato": 0, "Acertou Vencedor": 0, "Placar Perdedor": 0, "Artilheiros Certos": 0}
                        
                    # Se o jogo já tem resultado oficial, calcula a pontuação
                    if id_j in oficiais:
                        pts, stats = calcular_desempenho(p, oficiais[id_j])
                        tabela[user]["Pontuação Total"] += pts
                        tabela[user]["Placar Exato"] += stats["exato"]
                        tabela[user]["Acertou Vencedor"] += stats["vencedor"]
                        tabela[user]["Placar Perdedor"] += stats["perdedor"]
                        tabela[user]["Artilheiros Certos"] += stats["artilheiro"]

                if tabela:
                    df = pd.DataFrame.from_dict(tabela, orient='index')
                    df.index.name = 'Participante'
                    df = df.sort_values(by=["Pontuação Total", "Placar Exato"], ascending=[False, False])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Nenhuma pontuação computada ainda.")
            else:
                st.warning("Conecte o Firebase para ver o Ranking real.")
