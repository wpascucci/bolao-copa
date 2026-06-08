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
    
    if len(list(ref_jogos.limit(1).stream())) == 0:
        id_jogo = 1
        data_base = datetime(2026, 6, 11, 15, 0)
        
        for grupo, times in GRUPOS_2026.items():
            confrontos = [(0,1), (2,3), (0,2), (3,1), (3,0), (1,2)]
            for rodada, (i, j) in enumerate(confrontos):
                hora_jogo = data_base + timedelta(days=(id_jogo//4), hours=(id_jogo%4)*4)
                jogo = {
                    "id": f"jogo_{id_jogo}", "fase": "Grupos", "grupo": grupo,
                    "rodada": (rodada // 2) + 1, "time_a": times[i], "time_b": times[j],
                    "data_hora": hora_jogo.strftime("%Y-%m-%d %
