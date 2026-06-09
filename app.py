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

# --- GERAÇÃO DOS 72 JOGOS DA FASE DE GRUPOS COM HORÁRIOS ---
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
    
    # Se estiver vazio, cria a tabela oficial enviada com os horários de Brasília
    if len(list(ref_jogos.limit(1).stream())) == 0:
        batch = db.batch()
        
        JOGOS_BASE = [
            # 1ª Rodada
            {"id": "jogo_1", "fase": "Grupos", "grupo": "A", "time_a": "México", "time_b": "África do Sul", "data_hora": "2026-06-11 16:00"},
            {"id": "jogo_2", "fase": "Grupos", "grupo": "A", "time_a": "República da Coreia", "time_b": "República Tcheca", "data_hora": "2026-06-11 23:00"},
            {"id": "jogo_3", "fase": "Grupos", "grupo": "B", "time_a": "Canadá", "time_b": "Bósnia e Herzegovina", "data_hora": "2026-06-12 16:00"},
            {"id": "jogo_4", "fase": "Grupos", "grupo": "D", "time_a": "Estados Unidos", "time_b": "Paraguai", "data_hora": "2026-06-12 22:00"},
            {"id": "jogo_5", "fase": "Grupos", "grupo": "B", "time_a": "Catar", "time_b": "Suíça", "data_hora": "2026-06-13 16:00"},
            {"id": "jogo_6", "fase": "Grupos", "grupo": "C", "time_a": "Brasil", "time_b": "Marrocos", "data_hora": "2026-06-13 19:00"},
            {"id": "jogo_7", "fase": "Grupos", "grupo": "C", "time_a": "Haiti", "time_b": "Escócia", "data_hora": "2026-06-13 22:00"},
            {"id": "jogo_8", "fase": "Grupos", "grupo": "D", "time_a": "Austrália", "time_b": "Turquia", "data_hora": "2026-06-14 01:00"},
            {"id": "jogo_9", "fase": "Grupos", "grupo": "E", "time_a": "Alemanha", "time_b": "Curaçau", "data_hora": "2026-06-14 14:00"},
            {"id": "jogo_10", "fase": "Grupos", "grupo": "E", "time_a": "Costa do Marfim", "time_b": "Equador", "data_hora": "2026-06-14 20:00"},
            {"id": "jogo_11", "fase": "Grupos", "grupo": "F", "time_a": "Holanda", "time_b": "Japão", "data_hora": "2026-06-14 17:00"},
            {"id": "jogo_12", "fase": "Grupos", "grupo": "F", "time_a": "Suécia", "time_b": "Tunísia", "data_hora": "2026-06-14 23:00"},
            {"id": "jogo_13", "fase": "Grupos", "grupo": "H", "time_a": "Espanha", "time_b": "Cabo Verde", "data_hora": "2026-06-15 13:00"},
            {"id": "jogo_14", "fase": "Grupos", "grupo": "H", "time_a": "Arábia Saudita", "time_b": "Uruguai", "data_hora": "2026-06-15 19:00"},
            {"id": "jogo_15", "fase": "Grupos", "grupo": "G", "time_a": "Bélgica", "time_b": "Egito", "data_hora": "2026-06-15 16:00"},
            {"id": "jogo_16", "fase": "Grupos", "grupo": "G", "time_a": "Irã", "time_b": "Nova Zelândia", "data_hora": "2026-06-15 22:00"},
            {"id": "jogo_17", "fase": "Grupos", "grupo": "I", "time_a": "França", "time_b": "Senegal", "data_hora": "2026-06-16 16:00"},
            {"id": "jogo_18", "fase": "Grupos", "grupo": "I", "time_a": "Iraque", "time_b": "Noruega", "data_hora": "2026-06-16 19:00"},
            {"id": "jogo_19", "fase": "Grupos", "grupo": "J", "time_a": "Argentina", "time_b": "Argélia", "data_hora": "2026-06-16 22:00"},
            {"id": "jogo_20", "fase": "Grupos", "grupo": "J", "time_a": "Áustria", "time_b": "Jordânia", "data_hora": "2026-06-17 01:00"},
            {"id": "jogo_21", "fase": "Grupos", "grupo": "K", "time_a": "Portugal", "time_b": "República Democrática do Congo", "data_hora": "2026-06-17 14:00"},
            {"id": "jogo_22", "fase": "Grupos", "grupo": "L", "time_a": "Inglaterra", "time_b": "Croácia", "data_hora": "2026-06-17 17:00"},
            {"id": "jogo_23", "fase": "Grupos", "grupo": "L", "time_a": "Gana", "time_b": "Panamá", "data_hora": "2026-06-17 20:00"},
            {"id": "jogo_24", "fase": "Grupos", "grupo": "K", "time_a": "Uzbequistão", "time_b": "Colômbia", "data_hora": "2026-06-17 21:00"},
            
            # 2ª Rodada
            {"id": "jogo_25", "fase": "Grupos", "grupo": "A", "time_a": "República Tcheca", "time_b": "África do Sul", "data_hora": "2026-06-18 13:00"},
            {"id": "jogo_26", "fase": "Grupos", "grupo": "B", "time_a": "Suíça", "time_b": "Bósnia e Herzegovina", "data_hora": "2026-06-18 16:00"},
            {"id": "jogo_27", "fase": "Grupos", "grupo": "B", "time_a": "Canadá", "time_b": "Catar", "data_hora": "2026-06-18 19:00"},
            {"id": "jogo_28", "fase": "Grupos", "grupo": "A", "time_a": "México", "time_b": "República da Coreia", "data_hora": "2026-06-18 22:00"},
            {"id": "jogo_29", "fase": "Grupos", "grupo": "D", "time_a": "Turquia", "time_b": "Paraguai", "data_hora": "2026-06-19 00:00"},
            {"id": "jogo_30", "fase": "Grupos", "grupo": "D", "time_a": "Estados Unidos", "time_b": "Austrália", "data_hora": "2026-06-19 16:00"},
            {"id": "jogo_31", "fase": "Grupos", "grupo": "C", "time_a": "Escócia", "time_b": "Marrocos", "data_hora": "2026-06-19 19:00"},
            {"id": "jogo_32", "fase": "Grupos", "grupo": "C", "time_a": "Brasil", "time_b": "Haiti", "data_hora": "2026-06-19 21:30"},
            {"id": "jogo_33", "fase": "Grupos", "grupo": "F", "time_a": "Holanda", "time_b": "Suécia", "data_hora": "2026-06-20 14:00"},
            {"id": "jogo_34", "fase": "Grupos", "grupo": "E", "time_a": "Alemanha", "time_b": "Costa do Marfim", "data_hora": "2026-06-20 17:00"},
            {"id": "jogo_35", "fase": "Grupos", "grupo": "E", "time_a": "Equador", "time_b": "Curaçau", "data_hora": "2026-06-20 21:00"},
            {"id": "jogo_36", "fase": "Grupos", "grupo": "F", "time_a": "Tunísia", "time_b": "Japão", "data_hora": "2026-06-20 23:00"},
            {"id": "jogo_37", "fase": "Grupos", "grupo": "H", "time_a": "Espanha", "time_b": "Arábia Saudita", "data_hora": "2026-06-21 13:00"},
            {"id": "jogo_38", "fase": "Grupos", "grupo": "G", "time_a": "Bélgica", "time_b": "Irã", "data_hora": "2026-06-21 16:00"},
            {"id": "jogo_39", "fase": "Grupos", "grupo": "H", "time_a": "Uruguai", "time_b": "Cabo Verde", "data_hora": "2026-06-21 19:00"},
            {"id": "jogo_40", "fase": "Grupos", "grupo": "G", "time_a": "Nova Zelândia", "time_b": "Egito", "data_hora": "2026-06-21 22:00"},
            {"id": "jogo_41", "fase": "Grupos", "grupo": "J", "time_a": "Argentina", "time_b": "Áustria", "data_hora": "2026-06-22 14:00"},
            {"id": "jogo_42", "fase": "Grupos", "grupo": "I", "time_a": "França", "time_b": "Iraque", "data_hora": "2026-06-22 18:00"},
            {"id": "jogo_43", "fase": "Grupos", "grupo": "I", "time_a": "Noruega", "time_b": "Senegal", "data_hora": "2026-06-22 21:00"},
            {"id": "jogo_44", "fase": "Grupos", "grupo": "J", "time_a": "Jordânia", "time_b": "Argélia", "data_hora": "2026-06-23 00:00"},
            {"id": "jogo_45", "fase": "Grupos", "grupo": "K", "time_a": "Portugal", "time_b": "Uzbequistão", "data_hora": "2026-06-23 14:00"},
            {"id": "jogo_46", "fase": "Grupos", "grupo": "L", "time_a": "Inglaterra", "time_b": "Gana", "data_hora": "2026-06-23 17:00"},
            {"id": "jogo_47", "fase": "Grupos", "grupo": "L", "time_a": "Panamá", "time_b": "Croácia", "data_hora": "2026-06-23 20:00"},
            {"id": "jogo_48", "fase": "Grupos", "grupo": "K", "time_a": "Colômbia", "time_b": "República Democrática do Congo", "data_hora": "2026-06-23 23:00"},
            
            # 3ª Rodada
            {"id": "jogo_49", "fase": "Grupos", "grupo": "B", "time_a": "Suíça", "time_b": "Canadá", "data_hora": "2026-06-24 16:00"},
            {"id": "jogo_50", "fase": "Grupos", "grupo": "B", "time_a": "Bósnia e Herzegovina", "time_b": "Catar", "data_hora": "2026-06-24 16:00"},
            {"id": "jogo_51", "fase": "Grupos", "grupo": "C", "time_a": "Escócia", "time_b": "Brasil", "data_hora": "2026-06-24 19:00"},
            {"id": "jogo_52", "fase": "Grupos", "grupo": "C", "time_a": "Marrocos", "time_b": "Haiti", "data_hora": "2026-06-24 19:00"},
            {"id": "jogo_53", "fase": "Grupos", "grupo": "A", "time_a": "República Tcheca", "time_b": "México", "data_hora": "2026-06-24 22:00"},
            {"id": "jogo_54", "fase": "Grupos", "grupo": "A", "time_a": "África do Sul", "time_b": "República da Coreia", "data_hora": "2026-06-24 22:00"},
            {"id": "jogo_55", "fase": "Grupos", "grupo": "E", "time_a": "Equador", "time_b": "Alemanha", "data_hora": "2026-06-25 17:00"},
            {"id": "jogo_56", "fase": "Grupos", "grupo": "E", "time_a": "Curaçau", "time_b": "Costa do Marfim", "data_hora": "2026-06-25 17:00"},
            {"id": "jogo_57", "fase": "Grupos", "grupo": "F", "time_a": "Tunísia", "time_b": "Holanda", "data_hora": "2026-06-25 20:00"},
            {"id": "jogo_58", "fase": "Grupos", "grupo": "F", "time_a": "Japão", "time_b": "Suécia", "data_hora": "2026-06-25 20:00"},
            {"id": "jogo_59", "fase": "Grupos", "grupo": "D", "time_a": "Turquia", "time_b": "Estados Unidos", "data_hora": "2026-06-25 23:00"},
            {"id": "jogo_60", "fase": "Grupos", "grupo": "D", "time_a": "Paraguai", "time_b": "Austrália", "data_hora": "2026-06-25 23:00"},
            {"id": "jogo_61", "fase": "Grupos", "grupo": "I", "time_a": "Noruega", "time_b": "França", "data_hora": "2026-06-26 16:00"},
            {"id": "jogo_62", "fase": "Grupos", "grupo": "I", "time_a": "Senegal", "time_b": "Iraque", "data_hora": "2026-06-26 16:00"},
            {"id": "jogo_63", "fase": "Grupos", "grupo": "H", "time_a": "Uruguai", "time_b": "Espanha", "data_hora": "2026-06-26 21:00"},
            {"id": "jogo_64", "fase": "Grupos", "grupo": "H", "time_a": "Cabo Verde", "time_b": "Arábia Saudita", "data_hora": "2026-06-26 21:00"},
            {"id": "jogo_65", "fase": "Grupos", "grupo": "G", "time_a": "Egito", "time_b": "Irã", "data_hora": "2026-06-27 00:00"},
            {"id": "jogo_66", "fase": "Grupos", "grupo": "G", "time_a": "Nova Zelândia", "time_b": "Bélgica", "data_hora": "2026-06-27 00:00"},
            {"id": "jogo_67", "fase": "Grupos", "grupo": "L", "time_a": "Panamá", "time_b": "Inglaterra", "data_hora": "2026-06-27 18:00"},
            {"id": "jogo_68", "fase": "Grupos", "grupo": "L", "time_a": "Croácia", "time_b": "Gana", "data_hora": "2026-06-27 18:00"},
            {"id": "jogo_69", "fase": "Grupos", "grupo": "K", "time_a": "Colômbia", "time_b": "Portugal", "data_hora": "2026-06-27 20:30"},
            {"id": "jogo_70", "fase": "Grupos", "grupo": "K", "time_a": "República Democrática do Congo", "time_b": "Uzbequistão", "data_hora": "2026-06-27 20:30"},
            {"id": "jogo_71", "fase": "Grupos", "grupo": "J", "time_a": "Argélia", "time_b": "Áustria", "data_hora": "2026-06-27 23:00"},
            {"id": "jogo_72", "fase": "Grupos", "grupo": "J", "time_a": "Jordânia", "time_b": "Argentina", "data_hora": "2026-06-27 23:00"}
        ]
        
        for jogo in JOGOS_BASE:
            doc_ref = ref_jogos.document(jogo["id"])
            batch.set(doc_ref, jogo)
        
        batch.commit()
        
def carregar_jogos():
    if not db: return []
    inicializar_jogos_no_banco()
    docs = db.collection("tabela_jogos").stream()
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

# --- CÁLCULO DA TABELA DE CLASSIFICAÇÃO E PONTUAÇÃO ---
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
    data_hora_str = jogo.get('data_hora', '2026-12-31 23:59')
    hora_jogo = datetime.strptime(data_hora_str, "%Y-%m-%d %H:%M")
    tempo_atual = datetime.now()
    limite_aposta = hora_jogo - timedelta(minutes=10)
    jogo_bloqueado = tempo_atual > limite_aposta and not modo_admin
    
    doc_id = f"{jogo['id']}" if modo_admin else f"{email_usuario}_{jogo['id']}"
    col_ref = db.collection("resultados_oficiais" if modo_admin else "palpites") if db else None
    dados_existentes = col_ref.document(doc_id).get().to_dict() if col_ref and col_ref.document(doc_id).get().exists else None

    # Se o tempo esgotou e não é o admin
    if jogo_bloqueado:
        if dados_existentes:
            art_a = ", ".join(dados_existentes.get('artilheiros_a', [])) or "Nenhum"
            art_b = ", ".join(dados_existentes.get('artilheiros_b', [])) or "Nenhum"
            st.markdown(f"""
            <div class="locked-box">
                <b>🔒 Jogo Bloqueado (Tempo Esgotado)</b><br>
                <span style="font-size: 18px;">{jogo['time_a']} <b>{dados_existentes.get('placar_a',0)} x {dados_existentes.get('placar_b',0)}</b> {jogo['time_b']}</span><br>
                <div class="gols-text">⚽ Gols {jogo['time_a']}: <i>{art_a}</i></div>
                <div class="gols-text">⚽ Gols {jogo['time_b']}: <i>{art_b}</i></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"Tempo esgotado! As apostas fecharam em {limite_aposta.strftime('%d/%m às %H:%M')}. Pontuação: 0.")
        return

    # Se o tempo não esgotou, carrega os dados anteriores para edição (se existirem)
    valor_ga = dados_existentes.get('placar_a', 0) if dados_existentes else 0
    valor_gb = dados_existentes.get('placar_b', 0) if dados_existentes else 0

    st.markdown(f"**{jogo['time_a']} x {jogo['time_b']}**")
    if dados_existentes and not modo_admin:
        st.info("Você já palpitou, mas pode alterar à vontade até 10 minutos antes do jogo.")

    c2, c3 = st.columns([1, 1])
    ga = c2.number_input(f"Gols {jogo['time_a']}", min_value=0, step=1, value=valor_ga, key=f"ga_{jogo['id']}_{modo_admin}")
    gb = c3.number_input(f"Gols {jogo['time_b']}", min_value=0, step=1, value=valor_gb, key=f"gb_{jogo['id']}_{modo_admin}")
    
    art_a, art_b = [], []
    existentes_a = dados_existentes.get('artilheiros_a', []) if dados_existentes else []
    existentes_b = dados_existentes.get('artilheiros_b', []) if dados_existentes else []

    if ga > 0 or gb > 0:
        c_art_a, c_art_b = st.columns(2)
        with c_art_a:
            for i in range(ga): 
                valor_padrao = existentes_a[i] if i < len(existentes_a) else ""
                art_a.append(st.text_input(f"Gol {i+1} ({jogo['time_a']})", value=valor_padrao, key=f"aa_{jogo['id']}_{i}_{modo_admin}"))
        with c_art_b:
            for i in range(gb): 
                valor_padrao = existentes_b[i] if i < len(existentes_b) else ""
                art_b.append(st.text_input(f"Gol {i+1} ({jogo['time_b']})", value=valor_padrao, key=f"ab_{jogo['id']}_{i}_{modo_admin}"))

    aviso_tempo = f"(Fecha às {limite_aposta.strftime('%H:%M')})"
    texto_botao = "💾 Atualizar Palpite" if dados_existentes else "✅ Confirmar Palpite"
    if modo_admin:
        texto_botao = "💾 Salvar Oficial"

    if st.button(f"{texto_botao} {aviso_tempo if not modo_admin else ''}", key=f"btn_{jogo['id']}_{modo_admin}"):
        if (ga > 0 and "" in art_a) or (gb > 0 and "" in art_b): 
            st.error("Preencha o nome de todos os artilheiros!")
        elif db:
            col_ref.document(doc_id).set({"placar_a": ga, "placar_b": gb, "artilheiros_a": art_a, "artilheiros_b": art_b, "email": email_usuario, "nome_completo": nome_exibicao, "id_jogo": jogo['id']})
            st.success("Salvo com sucesso!"); st.rerun()
            
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
    abas = st.tabs(["⚙️ Lançar Resultados", "📊 Tabela e Mata-Mata", "📈 Ranking"] if st.session_state.is_admin else FASES_COPA + ["👁️ Palpites da Galera", "📈 Ranking"])

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
                    
        aba_ranking = abas[2]
        
    else:
        for i, fase in enumerate(FASES_COPA):
            with abas[i]:
                jogos_fase = [j for j in JOGOS_ATUAIS if j["fase"] == fase]
                for j in jogos_fase:
                    with st.expander(f"⚽ {j['time_a']} x {j['time_b']} 🕒 {j.get('data_hora', 'N/D')}"):
                        renderizar_jogo(j, st.session_state.usuario_logado, st.session_state.nome_usuario, False)
        
        aba_showdown = abas[-2]
        aba_ranking = abas[-1]

        # --- ABA PALPITES DA GALERA ---
        with aba_showdown:
            st.header("Mesa de Palpites")
            st.write("Visível somente após todos palpitarem ou se o tempo esgotar (10 min antes).")
            
            if JOGOS_ATUAIS:
                jogo_selecionado_str = st.selectbox("Selecione a partida:", [f"{j['id']} - {j['time_a']} x {j['time_b']}" for j in JOGOS_ATUAIS])
                jogo_id_sel = jogo_selecionado_str.split(" - ")[0]
                jogo_sel = next(j for j in JOGOS_ATUAIS if j["id"] == jogo_id_sel)
                
                if db:
                    total_usuarios = len(list(db.collection("usuarios").where("email", "!=", "admin").stream()))
                    palpites_jogo = list(db.collection("palpites").where("id_jogo", "==", jogo_id_sel).stream())
                    
                    data_hora_str = jogo_sel.get('data_hora', '2026-12-31 23:59')
                    hora_jogo = datetime.strptime(data_hora_str, "%Y-%m-%d %H:%M")
                    limite_esgotado = datetime.now() > (hora_jogo - timedelta(minutes=10))
                    todos_palpitaram = len(palpites_jogo) >= total_usuarios and total_usuarios > 0
                    
                    if todos_palpitaram or limite_esgotado:
                        st.success("Mesa Aberta! Confira os palpites:")
                        dados_tabela = []
                        for doc in palpites_jogo:
                            p = doc.to_dict()
                            artilheiros = ", ".join(p.get('artilheiros_a', []) + p.get('artilheiros_b', []))
                            dados_tabela.append({
                                # Correção exata do KeyError com o .get()
                                "Jogador": p.get('nome_completo', 'Desconhecido'),
                                "Placar": f"{jogo_sel['time_a']} {p.get('placar_a',0)} x {p.get('placar_b',0)} {jogo_sel['time_b']}",
                                "Goleadores": artilheiros if artilheiros else "Nenhum"
                            })
                        if dados_tabela:
                            st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True)
                        else:
                            st.info("Ninguém registrou palpites para este jogo.")
                    else:
                        faltam = total_usuarios - len(palpites_jogo)
                        st.warning(f"🔒 Bloqueado! Ainda faltam {faltam} jogadores. Aguarde todos finalizarem ou o relógio esgotar.")

        with aba_ranking:
            st.header("Classificação Geral")
            if st.button("🔄 Atualizar Ranking") and db:
                oficiais = {d.id: d.to_dict() for d in db.collection("resultados_oficiais").stream()}
                tabela = {}
                for doc in db.collection("palpites").stream():
                    p = doc.to_dict()
                    # Proteção adicional aqui também para evitar o KeyError
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
