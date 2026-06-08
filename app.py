import streamlit as st
import pandas as pd
import json
import re
import hashlib
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore

st.set_page_config(page_title="Bolão Copa 2026", page_icon="🏆", layout="wide")

st.markdown("""
    <style>
    .stButton>button { border-radius: 8px; font-weight: bold; }
    .locked-box { background-color: #e8f0fe; padding: 15px; border-radius: 10px; border-left: 5px solid #1a73e8; margin-bottom: 10px;}
    .gols-text { font-size: 14px; color: #555; margin-top: 5px; }
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

# --- DADOS COM HORÁRIO OFICIAL (Exemplo) ---
# Formato do horário: "YYYY-MM-DD HH:MM"
JOGOS_ATUAIS = [
    {"id": "jogo_1", "fase": "Grupos", "time_a": "México", "time_b": "África do Sul", "data_hora": "2026-06-11 15:00"},
    {"id": "jogo_2", "fase": "Grupos", "time_a": "Brasil", "time_b": "Marrocos", "data_hora": "2026-06-13 19:00"}
]

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
    # Verificação de tempo limite (10 minutos antes do jogo)
    hora_jogo = datetime.strptime(jogo['data_hora'], "%Y-%m-%d %H:%M")
    tempo_atual = datetime.now()
    limite_aposta = hora_jogo - timedelta(minutes=10)
    jogo_bloqueado = tempo_atual > limite_aposta and not modo_admin
    
    doc_id = f"{jogo['id']}" if modo_admin else f"{email_usuario}_{jogo['id']}"
    col_ref = db.collection("resultados_oficiais" if modo_admin else "palpites") if db else None
    dados_existentes = col_ref.document(doc_id).get().to_dict() if col_ref and col_ref.document(doc_id).get().exists else None

    # Se já tem palpite, exibe o placar e os artilheiros numa caixa fechada
    if dados_existentes and not modo_admin:
        art_a = ", ".join(dados_existentes.get('artilheiros_a', [])) or "Nenhum"
        art_b = ", ".join(dados_existentes.get('artilheiros_b', [])) or "Nenhum"
        
        st.markdown(f"""
        <div class="locked-box">
            <b>🔒 Palpite Registrado</b><br>
            <span style="font-size: 18px;">{jogo['time_a']} <b>{dados_existentes['placar_a']} x {dados_existentes['placar_b']}</b> {jogo['time_b']}</span><br>
            <div class="gols-text">⚽ Gols {jogo['time_a']}: <i>{art_a}</i></div>
            <div class="gols-text">⚽ Gols {jogo['time_b']}: <i>{art_b}</i></div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Se o tempo esgotou e o usuário não palpitou
    if jogo_bloqueado:
        st.warning(f"Tempo esgotado! As apostas para este jogo fecharam em {limite_aposta.strftime('%d/%m às %H:%M')}. Pontuação: 0.")
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
            st.success("Palpite registrado permanentemente!"); st.rerun()

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
    
    # Adicionamos a aba "Showdown" (Palpites da Galera)
    abas = st.tabs(["⚙️ Lançar Resultados"] if st.session_state.is_admin else FASES_COPA + ["👁️ Palpites da Galera", "📈 Ranking"])

    if st.session_state.is_admin:
        with abas[0]:
            fase_sel = st.selectbox("Fase:", FASES_COPA)
            for j in [j for j in JOGOS_ATUAIS if j["fase"] == fase_sel]:
                with st.expander(f"⚙️ {j['time_a']} x {j['time_b']} ({j['data_hora']})"):
                    renderizar_jogo(j, "admin", "Admin", True)
    else:
        # Abas de Fases de Grupos (Com a nova UX de Expanders)
        for i, fase in enumerate(FASES_COPA):
            with abas[i]:
                jogos_fase = [j for j in JOGOS_ATUAIS if j["fase"] == fase]
                for j in jogos_fase:
                    # UX Limpa: Cada jogo fica "escondido" até você clicar para expandir
                    with st.expander(f"⚽ {j['time_a']} x {j['time_b']} 🕒 {j['data_hora']}"):
                        renderizar_jogo(j, st.session_state.usuario_logado, st.session_state.nome_usuario, False)
        
        aba_showdown = abas[-2]
        aba_ranking = abas[-1]

        # --- ABA PALPITES DA GALERA (SHOWDOWN) ---
        with aba_showdown:
            st.header("Mesa de Palpites")
            st.write("Veja as apostas de todos os participantes. As informações só são reveladas se todos já palpitaram ou se o tempo limite do jogo (10 min antes do apito inicial) já passou.")
            
            jogo_selecionado_str = st.selectbox("Selecione a partida:", [f"{j['id']} - {j['time_a']} x {j['time_b']}" for j in JOGOS_ATUAIS])
            jogo_id_sel = jogo_selecionado_str.split(" - ")[0]
            jogo_sel = next(j for j in JOGOS_ATUAIS if j["id"] == jogo_id_sel)
            
            if db:
                total_usuarios = len(list(db.collection("usuarios").stream()))
                palpites_jogo = list(db.collection("palpites").where("id_jogo", "==", jogo_id_sel).stream())
                
                hora_jogo = datetime.strptime(jogo_sel['data_hora'], "%Y-%m-%d %H:%M")
                limite_esgotado = datetime.now() > (hora_jogo - timedelta(minutes=10))
                todos_palpitaram = len(palpites_jogo) >= total_usuarios
                
                if todos_palpitaram or limite_esgotado:
                    st.success("Mesa Aberta! Confira os palpites:")
                    dados_tabela = []
                    for doc in palpites_jogo:
                        p = doc.to_dict()
                        artilheiros = ", ".join(p.get('artilheiros_a', []) + p.get('artilheiros_b', []))
                        dados_tabela.append({
                            "Jogador": p['nome_completo'],
                            "Placar": f"{jogo_sel['time_a']} {p['placar_a']} x {p['placar_b']} {jogo_sel['time_b']}",
                            "Goleadores": artilheiros if artilheiros else "Nenhum"
                        })
                    
                    if dados_tabela:
                        st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True)
                    else:
                        st.info("Ninguém registrou palpites para este jogo.")
                else:
                    faltam = total_usuarios - len(palpites_jogo)
                    st.warning(f"🔒 Bloqueado! Ainda faltam {faltam} jogadores registrarem seus palpites. Aguarde todos finalizarem ou o relógio bater 10 minutos antes da partida.")
            else:
                st.warning("Conecte o Firebase para visualizar os palpites.")

        with aba_ranking:
            st.header("Classificação Geral")
            # Código do ranking mantido intacto aqui...
