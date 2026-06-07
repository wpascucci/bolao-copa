import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import json

# --- CONFIGURAÇÃO DO FIREBASE ---
# Para rodar localmente ou na nuvem de forma segura, usamos os Secrets do Streamlit
if not firebase_admin._apps:
    # Carrega as credenciais vindas do segredo do Streamlit
    try:
        firebase_creds = json.loads(st.secrets["firebase_credentials"])
        cred = credentials.Certificate(firebase_creds)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error("Erro ao carregar as credenciais do Firebase. Verifique as configurações de Secrets.")

# Inicializa o cliente do Firestore
try:
    db = firestore.client()
except Exception:
    st.warning("Banco de dados não conectado. Verifique a configuração.")

# --- LÓGICA DE PONTUAÇÃO ---
def calcular_pontos_partida(palpite_A, palpite_B, real_A, real_B):
    vencedor_palpite = 'A' if palpite_A > palpite_B else 'B' if palpite_B > palpite_A else 'Empate'
    vencedor_real = 'A' if real_A > real_B else 'B' if real_B > real_A else 'Empate'
    
    if palpite_A == real_A and palpite_B == real_B:
        return 25 
        
    pontos = 0
    if vencedor_palpite == vencedor_real:
        pontos += 10
        if (vencedor_real == 'A' and palpite_A == real_A) or \
           (vencedor_real == 'B' and palpite_B == real_B):
            pontos += 5 
            
    if (vencedor_real == 'A' and palpite_B == real_B) or \
       (vencedor_real == 'B' and palpite_A == real_A):
        pontos += 2

    return pontos

# --- INTERFACE DO APLICATIVO ---
st.title("🏆 Bolão Permanente da Copa")

# Identificação do Participante
st.header("👤 Quem está dando o palpite?")
nome_participante = st.text_input("Digite seu nome completo ou apelido:", key="nome_user").strip()

if nome_participante:
    st.write(f"Olá, **{nome_participante}**! Preencha seus palpites abaixo:")
    
    st.header("⚽ Palpite do Jogo")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Brasil")
        palpite_brasil = st.number_input("Gols do Brasil", min_value=0, step=1, key="g_br")
    with col2:
        st.markdown("<h3 style='text-align: center;'>X</h3>", unsafe_allow_html=True)
    with col3:
        st.subheader("Argentina")
        palpite_argentina = st.number_input("Gols da Argentina", min_value=0, step=1, key="g_ar")

    st.header("👟 Palpite de Artilheiros")
    st.write("Insira os gols previstos para os jogadores (Isso compõe o bônus de eliminação/campeão):")
    
    # Exemplo simples de estrutura de artilheiros
    jogador_1 = st.text_input("Nome do Jogador 1 (Ex: Neymar)", key="j1")
    gols_j1 = st.number_input("Gols do Jogador 1 no campeonato", min_value=0, step=1, key="gj1")
    
    if st.button("💾 Salvar Meu Palpite Permanentemente"):
        # Estrutura dos dados que vão para o Firebase
        dados_palpite = {
            "nome": nome_participante,
            "palpite_brasil": palpite_brasil,
            "palpite_argentina": palpite_argentina,
            "artilheiros": {
                jogador_1: gols_j1
            } if jogador_1 else {}
        }
        
        # Salva ou atualiza o documento no Firestore usando o nome do participante como ID único
        db.collection("palpites").document(nome_participante).set(dados_palpite)
        st.success(f"Palpite de {nome_participante} gravado com sucesso no banco de dados!")

else:
    st.info("Insira seu nome no campo acima para liberar o formulário de palpites.")

st.divider()

# --- VER TODOS OS PALPITES SALVOS (RANKING / LISTA) ---
st.header("📊 Palpites Cadastrados")
if st.button("🔄 Atualizar Lista de Palpites"):
    palpites_ref = db.collection("palpites").stream()
    lista_palpites = []
    
    for doc in palpites_ref:
        dados = doc.to_dict()
        lista_palpites.append({
            "Participante": dados.get("nome"),
            "Brasil": dados.get("palpite_brasil"),
            "Argentina": dados.get("palpite_argentina")
        })
    
    if lista_palpites:
        df = pd.DataFrame(lista_palpites)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Nenhum palpite encontrado no banco de dados ainda.")
