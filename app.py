import streamlit as st
import pandas as pd
import json
import re
import hashlib
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

# --- 1. CONFIGURAÇÃO (Sempre a primeira linha) ---
st.set_page_config(page_title="Bolão Copa 2026", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .locked-box { background-color: #e8f0fe; padding: 15px; border-radius: 10px; border-left: 5px solid #1a73e8; margin-bottom: 10px;}
    .gols-text { font-size: 14px; color: #555; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONEXÃO SEGURA COM FIREBASE ---
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            firebase_creds = json.loads(st.secrets["firebase_credentials"])
            cred = credentials.Certificate(firebase_creds)
            firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"⚠️ Erro nas credenciais do Firebase (Secrets): {e}")
        return None

db = init_firebase()

FASES_COPA = ["Grupos", "16 Avos", "Oitavas", "Quartas", "Semifinal", "Final"]

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

# --- 3. CARREGAMENTO OTIMIZADO (BATCH) ---
def carregar_jogos():
    if not db: return []
    try:
        ref_jogos = db.collection("tabela_jogos")
        
        # Se estiver vazio, cria tudo em 1 segundo usando BATCH
        if len(list(ref_jogos.limit(1).stream())) == 0:
            batch = db.batch()
            id_jogo = 1
            data_base = datetime(2026, 6, 11, 15, 0)
            
            for grupo, times in GRUPOS_2026.items():
                confrontos = [(0,1), (2,3), (0,2), (3,1), (3,0), (1,2)]
                for rodada, (i, j) in enumerate(confrontos):
                    hora_jogo = data_base + timedelta(days=(id_jogo//4), hours=(id_jogo%4)*4)
                    jogo = {
                        "id": f"jogo_{id_jogo}", "fase": "Grupos", "grupo": grupo,
                        "rodada": (rodada // 2) + 1, "time_a": times[i], "time_b": times[j],
                        "data_hora": hora_jogo.strftime("%Y-%m-%d %H:%M")
                    }
                    doc_ref = ref_jogos.document(jogo["id"])
                    batch.set(doc_ref, jogo)
                    id_jogo += 1
            
            batch.commit() # Envia os 72 jogos de uma vez só!
            
        docs = ref_jogos.stream()
        
        def ordenacao_segura(x):
            try: return int(x['id'].split('_')[1])
            except: return 9999
            
        return sorted([d.to_dict() for d in docs], key=ordenacao_segura)
    except Exception as e:
        st.error(f"Erro ao carregar o banco de dados: {e}")
        return []

JOGOS_ATUAIS = carregar_jogos()

# --- 4. CONTROLE DE SESSÃO E SEGURANÇA ---
if "usuario_logado" not in st.session_state: st.session_state.usuario_logado = None
if "nome_usuario" not in st.session_state: st.session_state.nome_usuario = None
if "is_admin" not in st.session_state: st.session_state.is_admin = False

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

# --- 5. CÁLCULOS MATEMÁTICOS ---
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
            ta, tb, ga, gb, g = j["time_a"], j["time_b"], res["placar_a"], res["placar_b"], j["grupo"]
            tabela[g][ta]["J"] += 1; tabela[g][tb]["J"] += 1
            tabela[g][ta]["GP"] += ga; tabela[g][tb]["GP"] += gb
            tabela[g][ta]["GC"] += gb; tabela[g][tb]["GC"] += ga
            tabela[g][ta]["SG"] += (ga - gb); tabela[g][tb]["SG"] += (gb - ga)
            if ga > gb: tabela[g][ta]["P"] += 3; tabela[g][ta]["V"] += 1; tabela[g][tb]["D"] += 1
            elif gb > ga: tabela[g][tb]["P"] += 3; tabela[g][tb]["V"] += 1; tabela[g][ta]["D"] += 1
            else: tabela[g][ta]["P"] += 1; tabela[g][tb]["P"] += 1; tabela[g][ta]["E"] += 1; tabela[g][tb]["E"] += 1
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

# --- 6. TELA DE AUTENTICAÇÃO ---
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

# --- 7. MOTOR DE INTERFACE DE JOGO ---
def renderizar_jogo(jogo, email_usuario, nome_exibicao, modo_admin=False):
    data_hora_str = jogo.get('data_hora', '2026-12-31 23:59')
    hora_jogo = datetime.strptime(data_hora_str, "%Y-%m-%d %H:%M")
    tempo_atual = datetime.now()
    limite_aposta = hora_jogo - timedelta(minutes=10)
    jogo_bloqueado = tempo_atual > limite_aposta and not modo_admin
    
    doc_id = f"{jogo['id']}" if modo_admin else f"{email_usuario}_{jogo['id']}"
    col_ref = db.collection("resultados_oficiais" if modo_admin else "palpites") if db else None
    dados_existentes = col_ref.document(doc_id).get().to_dict() if col_ref and col_ref.document(doc_id).get().exists else None

    if dados_existentes and not modo_admin:
        art_a = ", ".join(dados_existentes.get('artilheiros_a', [])) or "Nenhum"
        art_b = ", ".join(dados_existentes.get('artilheiros_b', [])) or "Nenhum"
        st.markdown(f"""
        <div class="locked-box">
            <b>🔒 Palpite Registrado</b><br>
            <span style="font-size: 18px;">{jogo['time_a']} <b>{dados_existentes.get('placar_a',0)} x {dados_existentes.get('placar_b',0)}</b> {jogo['time_b']}</span><br>
            <div class="gols-text">⚽ Gols {jogo['time_a']}: <i>{art_a}</i></div>
            <div class="gols-text">⚽ Gols {jogo['time_b']}: <i>{art_b}</i></div>
        </div>
        """, unsafe_allow_html=True)
        return

    if jogo_bloqueado:
        st.warning(f"Tempo esgotado! As apostas fecharam em {limite_aposta.strftime('%d/%m às %H:%M')}. Pontuação: 0.")
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

    aviso_tempo = f"(Fecha às {limite_aposta.strftime('%H:%M')})"
    if st.button("💾 Salvar Oficial" if modo_admin else f"✅ Confirmar Palpite {aviso_tempo}", key=f"btn_{jogo['id']}_{modo_admin}"):
        if (ga > 0 and "" in art_a) or (gb > 0 and "" in art_b): st.error("Preencha o nome de todos os artilheiros!")
        elif db:
            col_ref.document(doc_id).set({"placar_a": ga, "placar_b": gb, "artilheiros_a": art_a, "artilheiros_b": art_b, "email": email_usuario, "nome_completo": nome_exibicao, "id_jogo": jogo['id']})
            st.success("Registrado permanentemente!"); st.rerun()

# --- 8. APLICATIVO PRINCIPAL ---
if st.session_state.usuario_logado is None:
    tela_autenticacao()
else:
    c_user, c_out = st.columns([4, 1])
    c_user.write(f"👤 **{st.session_state.nome_usuario}**")
    if c_out.button("Sair"):
        st.session_state.update({"usuario_logado": None, "nome_usuario": None, "is_admin": False})
        st.rerun()

    st.title("🏆 Simulador Copa 2026")
    
    abas = st.tabs(["⚙️ Resultados", "📊 Mata-Mata", "🗑️ Gerenciar", "📈 Ranking"] if st.session_state.is_admin else FASES_COPA + ["👁️ Mesa", "📈 Ranking"])

    if st.session_state.is_admin:
        with abas[0]:
            fase_sel = st.selectbox("Fase:", FASES_COPA)
            for j in [j for j in JOGOS_ATUAIS if j["fase"] == fase_sel]:
                with st.expander(f"⚙️ {j['time_a']} x {j['time_b']} ({j.get('data_hora', 'N/D')})"):
                    renderizar_jogo(j, "admin", "Admin", True)
                    
        with abas[1]:
            st.subheader("Situação dos Grupos")
            tabela_calculada = calcular_tabela_grupos()
            for grupo, times in tabela_calculada.items():
                df_grupo = pd.DataFrame.from_dict(times, orient='index').sort_values(by=["P", "SG", "GP"], ascending=[False, False, False])
                st.write(f"**Grupo {grupo}**")
                st.dataframe(df_grupo)
            
            st.divider()
            st.subheader("Gerar Mata-Mata")
            c_fase, c_ta, c_tb, c_data, c_btn = st.columns([2, 2, 2, 2, 2])
            nova_fase = c_fase.selectbox("Fase Destino", ["16 Avos", "Oitavas", "Quartas", "Semifinal", "Final"])
            novo_ta = c_ta.text_input("Time A")
            novo_tb = c_tb.text_input("Time B")
            nova_data = c_data.text_input("Data/Hora (YYYY-MM-DD HH:MM)", value="2026-06-30 15:00")
            if c_btn.button("Criar Confronto", use_container_width=True):
                if db and novo_ta and novo_tb:
                    novo_id = f"jogo_{len(JOGOS_ATUAIS) + 1}"
                    db.collection("tabela_jogos").document(novo_id).set({
                        "id": novo_id, "fase": nova_fase, "time_a": novo_ta.strip(), "time_b": novo_tb.strip(), "data_hora": nova_data
                    })
                    st.success("Confronto gerado!"); st.rerun()
                    
        with abas[2]:
            st.subheader("🗑️ Excluir Palpite de Usuário")
            if db:
                usuarios_docs = db.collection("usuarios").where("email", "!=", "admin").stream()
                lista_usuarios = {doc.to_dict()['email']: doc.to_dict().get('nome_completo', doc.id) for doc in usuarios_docs}
                
                if not lista_usuarios: st.info("Nenhum usuário cadastrado.")
                else:
                    email_alvo = st.selectbox("1. Usuário:", options=list(lista_usuarios.keys()), format_func=lambda x: lista_usuarios[x])
                    palpites_usuario = list(db.collection("palpites").where("email", "==", email_alvo).stream())
                    
                    if not palpites_usuario: st.info("Sem palpites.")
                    else:
                        opcoes_palpites = {}
                        for p in palpites_usuario:
                            dados_p = p.to_dict()
                            id_j = dados_p.get('id_jogo', '')
                            nome_j = next((f"{j['time_a']} x {j['time_b']}" for j in JOGOS_ATUAIS if j['id'] == id_j), id_j)
                            opcoes_palpites[p.id] = f"{nome_j} | Placar: {dados_p.get('placar_a',0)} x {dados_p.get('placar_b',0)}"
                        
                        id_palpite_excluir = st.selectbox("2. Palpite:", options=list(opcoes_palpites.keys()), format_func=lambda x: opcoes_palpites[x])
                        if st.button("🗑️ Confirmar Exclusão", type="primary"):
                            db.collection("palpites").document(id_palpite_excluir).delete()
                            st.success("Excluído com sucesso!"); st.rerun()
            else: st.error("Conecte
