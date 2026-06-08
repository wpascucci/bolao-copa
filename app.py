import streamlit as st
import pandas as pd
import json
import re
import hashlib
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="Bolão Copa 2026", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .locked-box { background-color: #e8f0fe; padding: 15px; border-radius: 10px; border-left: 5px solid #1a73e8; margin-bottom: 15px;}
    </style>
""", unsafe_allow_html=True)

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

# --- GERAÇÃO DOS 72 JOGOS DA FASE DE GRUPOS ---
GRUPOS_2026 = {
    "A": ["México", "África do Sul", "Coreia do Sul", "República Tcheca"],
    "B": ["Canadá", "Bósnia", "Catar", "Suíça"],
    "C": ["Brasil", "Marrocos", "Haiti", "Escócia"],
    "D": ["EUA", "Paraguai", "Austrália", "Turquia"],
    "E": ["Alemanha", "Curaçao", "Costa do Marfim", "Equador"],
    "F": ["Holanda", "Japão", "Suécia", "Tunísia"],
    "G": ["Bélgica", "Egito", "Irã", "Nova Zelândia"],
    "H": ["Espanha", "Cabo Verde", "Arábia Saudita", "Uruguai"],
    "I": ["França", "Senegal", "Iraque", "Noruega"],
    "J": ["Argentina", "Argélia", "Áustria", "Jordânia"],
    "K": ["Portugal", "RD Congo", "Uzbequistão", "Colômbia"],
    "L": ["Inglaterra", "Croácia", "Gana", "Panamá"]
}

def inicializar_jogos_no_banco():
    if not db: return
    ref_jogos = db.collection("tabela_jogos")
    if len(list(ref_jogos.limit(1).stream())) == 0:
        id_jogo = 1
        for grupo, times in GRUPOS_2026.items():
            confrontos = [(0,1), (2,3), (0,2), (3,1), (3,0), (1,2)]
            for rodada, (i, j) in enumerate(confrontos):
                jogo = {
                    "id": f"jogo_{id_jogo}", "fase": "Grupos", "grupo": grupo,
                    "rodada": (rodada // 2) + 1, "time_a": times[i], "time_b": times[j]
                }
                ref_jogos.document(jogo["id"]).set(jogo)
                id_jogo += 1

def carregar_jogos():
    if not db: return []
    inicializar_jogos_no_banco()
    docs = db.collection("tabela_jogos").stream()
    # Ordena pelo ID para manter a ordem lógica (jogo_1, jogo_2...)
    return sorted([d.to_dict() for d in docs], key=lambda x: int(x['id'].split('_')[1]))

JOGOS_ATUAIS = carregar_jogos()

# --- CONTROLE DE SESSÃO ---
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = None
if "nome_usuario" not in st.session_state: st.session_state.nome_usuario = None
if "is_admin" not in st.session_state: st.session_state.is_admin = False

# --- FUNÇÕES DE SEGURANÇA E VALIDAÇÃO ---
def gerar_hash(senha): return hashlib.sha256(senha.encode()).hexdigest()

def validar_cpf(cpf_str):
    cpf = re.sub(r'[^0-9]', '', str(cpf_str))
    if len(cpf) != 11 or cpf == cpf[0] * 11: return False
    def calc_dig(cpf_parcial, mults):
        resto = sum(int(d) * m for d, m in zip(cpf_parcial, mults)) % 11
        return 0 if resto < 2 else 11 - resto
    d1 = calc_dig(cpf[:9], range(10, 1, -1))
    d2 = calc_dig(cpf[:9] + str(d1), range(11, 1, -1))
    return cpf.endswith(f"{d1}{d2}")

# --- CÁLCULO DA TABELA DE CLASSIFICAÇÃO ---
def calcular_tabela_grupos():
    tabela = {}
    if not db: return tabela
    oficiais = {d.id: d.to_dict() for d in db.collection("resultados_oficiais").stream()}
    
    for grupo, times in GRUPOS_2026.items():
        tabela[grupo] = {t: {"P": 0, "J": 0, "V": 0, "E": 0, "D": 0, "GP": 0, "GC": 0, "SG": 0} for t in times}
        
    jogos_grupos = [j for j in JOGOS_ATUAIS if j["fase"] == "Grupos"]
    for j in jogos_grupos:
        if j["id"] in oficiais:
            res = oficiais[j["id"]]
            ta, tb = j["time_a"], j["time_b"]
            ga, gb = res["placar_a"], res["placar_b"]
            g = j["grupo"]
            
            tabela[g][ta]["J"] += 1; tabela[g][tb]["J"] += 1
            tabela[g][ta]["GP"] += ga; tabela[g][tb]["GP"] += gb
            tabela[g][ta]["GC"] += gb; tabela[g][tb]["GC"] += ga
            tabela[g][ta]["SG"] += (ga - gb); tabela[g][tb]["SG"] += (gb - ga)
            
            if ga > gb:
                tabela[g][ta]["P"] += 3; tabela[g][ta]["V"] += 1; tabela[g][tb]["D"] += 1
            elif gb > ga:
                tabela[g][tb]["P"] += 3; tabela[g][tb]["V"] += 1; tabela[g][ta]["D"] += 1
            else:
                tabela[g][ta]["P"] += 1; tabela[g][tb]["P"] += 1
                tabela[g][ta]["E"] += 1; tabela[g][tb]["E"] += 1
                
    return tabela

def calcular_desempenho(palpite, oficial):
    p_a, p_b = palpite.get('placar_a', 0), palpite.get('placar_b', 0)
    o_a, o_b = oficial.get('placar_a', 0), oficial.get('placar_b', 0)
    pts, stats = 0, {"exato": 0, "vencedor": 0, "perdedor": 0, "artilheiro": 0}
    
    vp = 'A' if p_a > p_b else 'B' if p_b > p_a else 'E'
    vo = 'A' if o_a > o_b else 'B' if o_b > o_a else 'E'
    
    if p_a == o_a and p_b == o_b: pts += 25; stats["exato"] = 1
    else:
        if vp == vo:
            pts += 10; stats["vencedor"] = 1
            if (vo == 'A' and p_a == o_a) or (vo == 'B' and p_b == o_b): pts += 5
        if (vo == 'A' and p_b == o_b) or (vo == 'B' and p_a == o_a): pts += 2; stats["perdedor"] = 1

    art_p = [a.strip().lower() for a in palpite.get('artilheiros_a', []) + palpite.get('artilheiros_b', []) if a]
    art_o = [a.strip().lower() for a in oficial.get('artilheiros_a', []) + oficial.get('artilheiros_b', []) if a]
    for jg in art_p:
        if jg in art_o: pts += 5; stats["artilheiro"] += 1; art_o.remove(jg) 
    return pts, stats

# --- TELA DE AUTENTICAÇÃO ---
def tela_autenticacao():
    st.title("⚽ Bolão Copa do Mundo 2026")
    tab_login, tab_cadastro = st.tabs(["🔑 Entrar", "📝 Cadastrar"])
    
    with tab_login:
        with st.container(border=True):
            email_login = st.text_input("E-mail (Ou 'admin')").strip().lower()
            senha_login = st.text_input("Senha", type="password")
            if st.button("Acessar", use_container_width=True):
                if email_login == "admin" and senha_login == "admin123":
                    st.session_state.update({"usuario_logado": "admin", "nome_usuario": "Administrador", "is_admin": True})
                    st.rerun()
                elif email_login and senha_login and db:
                    doc = db.collection("usuarios").document(email_login).get()
                    if doc.exists and doc.to_dict()["senha"] == gerar_hash(senha_login):
                        st.session_state.update({"usuario_logado": email_login, "nome_usuario": doc.to_dict()["nome_completo"], "is_admin": False})
                        st.rerun()
                    else: st.error("E-mail ou senha incorretos.")
    
    with tab_cadastro:
        with st.container(border=True):
            nome_cad = st.text_input("Nome Completo", key="c_nome").strip()
            email_cad = st.text_input("E-mail", key="c_email").strip().lower()
            cpf_cad = st.text_input("CPF", key="c_cpf").strip()
            senha_cad = st.text_input("Senha", type="password", key="c_senha")
            if st.button("Criar Minha Conta", type="primary", use_container_width=True):
                if not all([nome_cad, email_cad, cpf_cad, senha_cad]): st.error("Preencha tudo.")
                elif not validar_cpf(cpf_cad): st.error("CPF Inválido.")
                elif db:
                    cpf_l = re.sub(r'[^0-9]', '', cpf_cad)
                    if db.collection("usuarios").document(email_cad).get().exists: st.error("E-mail em uso.")
                    elif len(db.collection("usuarios").where("cpf", "==", cpf_l).get()) > 0: st.error("CPF em uso.")
                    else:
                        db.collection("usuarios").document(email_cad).set({"nome_completo": nome_cad, "email": email_cad, "cpf": cpf_l, "senha": gerar_hash(senha_cad)})
                        st.success("Conta criada! Faça login.")

# --- MOTOR DE INTERFACE DE JOGO ---
def renderizar_jogo(jogo, email_usuario, nome_exibicao, modo_admin=False):
    st.markdown(f"**{jogo['time_a']} x {jogo['time_b']}**")
    doc_id = f"{jogo['id']}" if modo_admin else f"{email_usuario}_{jogo['id']}"
    col_ref = db.collection("resultados_oficiais" if modo_admin else "palpites") if db else None
    dados_existentes = col_ref.document(doc_id).get().to_dict() if col_ref and col_ref.document(doc_id).get().exists else None

    if dados_existentes and not modo_admin:
        st.markdown(f"""<div class="locked-box"><b>🔒 Palpite Confirmado!</b><br>
        Placar: {jogo['time_a']} {dados_existentes['placar_a']} x {dados_existentes['placar_b']} {jogo['time_b']}</div>""", unsafe_allow_html=True)
        st.divider()
        return

    c2, c3 = st.columns([1, 1])
    ga = c2.number_input(f"Gols {jogo['time_a']}", min_value=0, step=1, key=f"ga_{jogo['id']}_{modo_admin}")
    gb = c3.number_input(f"Gols {jogo['time_b']}", min_value=0, step=1, key=f"gb_{jogo['id']}_{modo_admin}")
    
    art_a, art_b = [], []
    if ga > 0 or gb > 0:
        c_art_a, c_art_b = st.columns(2)
        with c_art_a:
            for i in range(ga): art_a.append(st.text_input(f"Gol {i+1} ({jogo['time_a']})", key=f"aa_{jogo['id']}_{i}_{modo_admin}"))
        with c_art_b:
            for i in range(gb): art_b.append(st.text_input(f"Gol {i+1} ({jogo['time_b']})", key=f"ab_{jogo['id']}_{i}_{modo_admin}"))

    if st.button("💾 Salvar Oficial" if modo_admin else "✅ Confirmar Palpite", key=f"btn_{jogo['id']}_{modo_admin}"):
        if (ga > 0 and "" in art_a) or (gb > 0 and "" in art_b): st.error("Preencha os artilheiros!")
        elif db:
            col_ref.document(doc_id).set({"placar_a": ga, "placar_b": gb, "artilheiros_a": art_a, "artilheiros_b": art_b, "email": email_usuario, "nome_completo": nome_exibicao, "id_jogo": jogo['id']})
            st.success("Salvo!"); st.rerun()
    st.divider()

# --- APLICATIVO PRINCIPAL ---
if st.session_state.usuario_logado is None:
    tela_autenticacao()
else:
    c_user, c_out = st.columns([4, 1])
    c_user.write(f"👤 **{st.session_state.nome_usuario}**")
    if c_out.button("Sair"):
        st.session_state.update({"usuario_logado": None, "nome_usuario": None, "is_admin": False})
        st.rerun()

    st.title("🏆 Simulador Copa 2026")
    abas = st.tabs(["⚙️ Lançar Resultados", "📊 Tabela e Mata-Mata", "📈 Ranking"] if st.session_state.is_admin else FASES_COPA + ["📈 Ranking"])

    if st.session_state.is_admin:
        with abas[0]:
            fase_sel = st.selectbox("Fase:", FASES_COPA)
            for j in [j for j in JOGOS_ATUAIS if j["fase"] == fase_sel]:
                renderizar_jogo(j, "admin", "Admin", True)
                
        with abas[1]:
            st.subheader("Situação dos Grupos")
            tabela_calculada = calcular_tabela_grupos()
            
            for grupo, times in tabela_calculada.items():
                df_grupo = pd.DataFrame.from_dict(times, orient='index')
                df_grupo = df_grupo.sort_values(by=["P", "SG", "GP"], ascending=[False, False, False])
                st.write(f"**Grupo {grupo}**")
                st.dataframe(df_grupo)
            
            st.divider()
            st.subheader("Gerar Mata-Mata")
            st.info("De acordo com os resultados oficiais, crie os próximos confrontos abaixo para liberar os palpites aos usuários.")
            c_fase, c_ta, c_tb, c_btn = st.columns([2, 3, 3, 2])
            nova_fase = c_fase.selectbox("Fase Destino", ["16 Avos", "Oitavas", "Quartas", "Semifinal", "Final"])
            novo_ta = c_ta.text_input("Time A (Ex: Brasil)")
            novo_tb = c_tb.text_input("Time B (Ex: França)")
            if c_btn.button("Criar Confronto", use_container_width=True):
                if db and novo_ta and novo_tb:
                    novo_id = f"jogo_{len(JOGOS_ATUAIS) + 1}"
                    db.collection("tabela_jogos").document(novo_id).set({
                        "id": novo_id, "fase": nova_fase, "time_a": novo_ta.strip(), "time_b": novo_tb.strip()
                    })
                    st.success("Confronto gerado com sucesso!")
                    st.rerun()
                    
        aba_ranking = abas[2]
        
    else:
        for i, fase in enumerate(FASES_COPA):
            with abas[i]:
                jogos_fase = [j for j in JOGOS_ATUAIS if j["fase"] == fase]
                if not jogos_fase: st.info("Jogos desta fase ainda não definidos pelo Admin.")
                for j in jogos_fase: renderizar_jogo(j, st.session_state.usuario_logado, st.session_state.nome_usuario, False)
        aba_ranking = abas[-1]

    with aba_ranking:
        st.header("Classificação Geral")
        if st.button("🔄 Atualizar Ranking") and db:
            oficiais = {d.id: d.to_dict() for d in db.collection("resultados_oficiais").stream()}
            tabela = {}
            for doc in db.collection("palpites").stream():
                p = doc.to_dict()
                nj = p.get('nome_completo', 'Desconhecido')
                id_j = p.get('id_jogo')
                if nj not in tabela: tabela[nj] = {"Pontos": 0, "Exatos": 0, "Vencedor": 0, "Perdedor": 0, "Artilheiros": 0}
                if id_j in oficiais:
                    pts, s = calcular_desempenho(p, oficiais[id_j])
                    tabela[nj]["Pontos"] += pts; tabela[nj]["Exatos"] += s["exato"]; tabela[nj]["Vencedor"] += s["vencedor"]
                    tabela[nj]["Perdedor"] += s["perdedor"]; tabela[nj]["Artilheiros"] += s["artilheiro"]
            if tabela:
                df = pd.DataFrame.from_dict(tabela, orient='index').sort_values(by=["Pontos", "Exatos"], ascending=[False, False])
                st.dataframe(df, use_container_width=True)
            else: st.info("Nenhuma pontuação computada.")
