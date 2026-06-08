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
            
            batch.commit()
            
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
    
    if p_a == o_a and p_b == o_b: 
        pts += 25
        stats["exato"] = 1
    else:
        if vp == vo:
            pts += 10
            stats["vencedor"] = 1
            if (vo == 'A' and p_a == o_a) or (vo == 'B' and p_b == o_b): 
                pts += 5
        if (vo == 'A' and p_b == o_b) or (vo == 'B' and p_a == o_a): 
            pts += 2
            stats["perdedor"] = 1

    art_p = [a.strip().lower() for a in palpite.get('artilheiros_a', []) + palpite.get('artilheiros_b', []) if a]
    art_o = [a.strip().lower() for a in oficial.get('artilheiros_a', []) + oficial.get('artilheiros_b', []) if a]
    
    for jg in art_p:
        if jg in art_o: 
            pts += 5
            stats["artilheiro"] += 1
            art_o.remove(jg) 
            
    return pts, stats
