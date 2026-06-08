import streamlit as st
import pandas as pd
import json
import re
import hashlib
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

# --- DADOS DA COPA ---
FASES_COPA = ["Grupos", "16 Avos", "Oitavas", "Quartas", "Semifinal", "Final"]
JOGOS = [
    {"id": "jogo_1", "fase": "Grupos", "time_a": "México", "time_b": "África do Sul"},
    {"id": "jogo_2", "fase": "Grupos", "time_a": "Brasil", "time_b": "Marrocos"}
]

# --- CONTROLE DE SESSÃO ---
if "usuario_logado" not in st.session_state:
    st.session_state.usuario_logado = None # Vai guardar o email
if "nome_usuario" not in st.session_state:
    st.session_state.nome_usuario = None # Vai guardar o nome completo
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# --- FUNÇÕES DE SEGURANÇA E VALIDAÇÃO ---
def gerar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def validar_cpf(cpf_str):
    cpf = re.sub(r'[^0-9]', '', str(cpf_str))
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    
    def calcular_digito(cpf_parcial, multiplicadores):
        soma = sum(int(digito) * mult for digito, mult in zip(cpf_parcial, multiplicadores))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    digito1 = calcular_digito(cpf[:9], range(10, 1, -1))
    digito2 = calcular_digito(cpf[:9] + str(digito1), range(11, 1, -1))
    
    return cpf.endswith(f"{digito1}{digito2}")

# --- TELA DE LOGIN E CADASTRO ---
def tela_autenticacao():
    st.title("⚽ Bolão Copa do Mundo 2026")
    
    tab_login, tab_cadastro = st.tabs(["🔑 Entrar", "📝 Cadastrar"])
    
    with tab_login:
        with st.container(border=True):
            email_login = st.text_input("E-mail (Ou 'admin' para controle)").strip().lower()
            senha_login = st.text_input("Senha", type="password")
            
            if st.button("Acessar", use_container_width=True):
                # Hardcode para o Admin
                if email_login == "admin" and senha_login == "admin123":
                    st.session_state.usuario_logado = "admin"
                    st.session_state.nome_usuario = "Administrador"
                    st.session_state.is_admin = True
                    st.rerun()
                elif email_login and senha_login:
                    if db:
                        doc_ref = db.collection("usuarios").document(email_login)
                        doc = doc_ref.get()
                        if doc.exists:
                            dados_user = doc.to_dict()
                            if dados_user["senha"] == gerar_hash(senha_login):
                                st.session_state.usuario_logado = email_login
                                st.session_state.nome_usuario = dados_user["nome_completo"]
                                st.session_state.is_admin = False
                                st.rerun()
                            else:
                                st.error("Senha incorreta.")
                        else:
                            st.error("Usuário não encontrado.")
                    else:
                        st.warning("Conecte o banco de dados para testar o login.")
    
    with tab_cadastro:
        with st.container(border=True):
            nome_cad = st.text_input("Nome Completo", key="cad_nome").strip()
            email_cad = st.text_input("E-mail", key="cad_email").strip().lower()
            cpf_cad = st.text_input("CPF (Apenas números ou com pontuação)", key="cad_cpf").strip()
            senha_cad = st.text_input("Crie uma Senha", type="password", key="cad_senha")
            
            if st.button("Criar Minha Conta", type="primary", use_container_width=True):
                if not nome_cad or not email_cad or not cpf_cad or not senha_cad:
                    st.error("Preencha todos os campos obrigatórios.")
                elif not validar_cpf(cpf_cad):
                    st.error("CPF Inválido. Verifique a numeração.")
                else:
                    if db:
                        cpf_limpo = re.sub(r'[^0-9]', '', cpf_cad)
                        
                        # Verifica se E-mail já existe
                        if db.collection("usuarios").document(email_cad).get().exists:
                            st.error("Este e-mail já está cadastrado.")
                        else:
                            # Verifica se CPF já existe
                            cpf_existente = db.collection("usuarios").where("cpf", "==", cpf_limpo).get()
                            if len(cpf_existente) > 0:
                                st.error("Este CPF já está cadastrado no sistema.")
                            else:
                                # Cadastra com sucesso
                                dados_novo_user = {
                                    "nome_completo": nome_cad,
                                    "email": email_cad,
                                    "cpf": cpf_limpo,
                                    "senha": gerar_hash(senha_cad)
                                }
                                db.collection("usuarios").document(email_cad).set(dados_novo_user)
                                st.success("Conta criada com sucesso! Faça login na aba 'Entrar'.")
                    else:
                        st.warning("Conecte o banco de dados para habilitar o cadastro.")

# --- LÓGICA DE PONTUAÇÃO MATEMÁTICA ---
def calcular_desempenho(palpite, oficial):
    p_a, p_b = palpite.get('placar_a', 0), palpite.get('placar_b', 0)
    o_a, o_b = oficial.get('placar_a', 0), oficial.get('placar_b', 0)
    
    pontos = 0
    stats = {"exato": 0, "vencedor": 0, "perdedor": 0, "artilheiro": 0}
    
    vencedor_p = 'A' if p_a > p_b else 'B' if p_b > p_a else 'E'
    vencedor_o = 'A' if o_a > o_b else 'B' if o_b > o_a else 'E'
    
    if p_a == o_a and p_b == o_b:
        pontos += 25
        stats["exato"] = 1
    else:
        if vencedor_p == vencedor_o:
            pontos += 10
            stats["vencedor"] = 1
            if (vencedor_o == 'A' and p_a == o_a) or (vencedor_o == 'B' and p_b == o_b):
                pontos += 5
        if (vencedor_o == 'A' and p_b == o_b) or (vencedor_o == 'B' and p_a == o_a):
            pontos += 2
            stats["perdedor"] = 1

    art_p = [a.strip().lower() for a in palpite.get('artilheiros_a', []) + palpite.get('artilheiros_b', []) if a]
    art_o = [a.strip().lower() for a in oficial.get('artilheiros_a', []) + oficial.get('artilheiros_b', []) if a]
    
    for jogador in art_p:
        if jogador in art_o:
            pontos += 5
            stats["artilheiro"] += 1
            art_o.remove(jogador) 
            
    return pontos, stats

# --- MOTOR DE INTERFACE DE JOGO ---
def renderizar_jogo(jogo, email_usuario, nome_exibicao, modo_admin=False):
    st.markdown(f"**{jogo['time_a']} x {jogo['time_b']}**")
    
    colecao = "resultados_oficiais" if modo_admin else "palpites"
    doc_id = f"{jogo['id']}" if modo_admin else f"{email_usuario}_{jogo['id']}"
    
    doc_ref = db.collection(colecao).document(doc_id) if db else None
    dados_existentes = doc_ref.get().to_dict() if (doc_ref and doc_ref.get().exists) else None

    # Bloqueio de edição
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
                dados = {
                    "placar_a": gols_a, "placar_b": gols_b, 
                    "artilheiros_a": art_a, "artilheiros_b": art_b, 
                    "email": email_usuario, "nome_completo": nome_exibicao, "id_jogo": jogo['id']
                }
                doc_ref.set(dados)
                st.success("Salvo com sucesso!")
                st.rerun()
    st.divider()

# --- APLICATIVO PRINCIPAL ---
if st.session_state.usuario_logado is None:
    tela_autenticacao()
else:
    c_user, c_out = st.columns([4, 1])
    c_user.write(f"👤 Jogador: **{st.session_state.nome_usuario}**")
    if c_out.button("Deslogar (Sair)"):
        st.session_state.usuario_logado = None
        st.session_state.nome_usuario = None
        st.session_state.is_admin = False
        st.rerun()

    st.title("🏆 Simulador Copa 2026")

    nomes_abas = ["⚙️ ADMIN", "📊 RANKING"] if st.session_state.is_admin else FASES_COPA + ["📊 RANKING"]
    abas = st.tabs(nomes_abas)

    if st.session_state.is_admin:
        with abas[0]:
            st.subheader("Área Restrita - Lançar Resultados Oficiais")
            fase_sel = st.selectbox("Fase:", FASES_COPA)
            for jogo in [j for j in JOGOS if j["fase"] == fase_sel]:
                renderizar_jogo(jogo, "admin", "Administrador", modo_admin=True)
        aba_ranking = abas[1]
    else:
        for i, fase in enumerate(FASES_COPA):
            with abas[i]:
                st.subheader(f"Partidas - {fase}")
                for jogo in [j for j in JOGOS if j["fase"] == fase]:
                    renderizar_jogo(jogo, st.session_state.usuario_logado, st.session_state.nome_usuario, modo_admin=False)
        aba_ranking = abas[-1]

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
                    # A chave da tabela agora é o NOME COMPLETO do usuário
                    nome_jogador = p.get('nome_completo', 'Jogador Desconhecido')
                    id_j = p.get('id_jogo')
                    
                    if nome_jogador not in tabela:
                        tabela[nome_jogador] = {"Pontuação Total": 0, "Placar Exato": 0, "Acertou Vencedor": 0, "Placar Perdedor": 0, "Artilheiros Certos": 0}
                        
                    if id_j in oficiais:
                        pts, stats = calcular_desempenho(p, oficiais[id_j])
                        tabela[nome_jogador]["Pontuação Total"] += pts
                        tabela[nome_jogador]["Placar Exato"] += stats["exato"]
                        tabela[nome_jogador]["Acertou Vencedor"] += stats["vencedor"]
                        tabela[nome_jogador]["Placar Perdedor"] += stats["perdedor"]
                        tabela[nome_jogador]["Artilheiros Certos"] += stats["artilheiro"]

                if tabela:
                    df = pd.DataFrame.from_dict(tabela, orient='index')
                    df.index.name = 'Participante'
                    df = df.sort_values(by=["Pontuação Total", "Placar Exato"], ascending=[False, False])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Nenhuma pontuação computada ainda.")
