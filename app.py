import streamlit as st
import pandas as pd

# --- LÓGICA DE PONTUAÇÃO ---
def calcular_pontos_partida(palpite_A, palpite_B, real_A, real_B):
    pontos = 0
    
    # Determinar Vencedores
    vencedor_palpite = 'A' if palpite_A > palpite_B else 'B' if palpite_B > palpite_A else 'Empate'
    vencedor_real = 'A' if real_A > real_B else 'B' if real_B > real_A else 'Empate'
    
    # 1. Placar Exato (Maior Pontuação: Ex: 25 pts)
    if palpite_A == real_A and palpite_B == real_B:
        return 25 
        
    # 2 e 3. Acertou o Vencedor (ou o Empate)
    if vencedor_palpite == vencedor_real:
        pontos += 10 # Pontuação base por acertar quem ganha (ou se empatou)
        
        # Acertou o Vencedor + Gols do Vencedor
        if (vencedor_real == 'A' and palpite_A == real_A) or \
           (vencedor_real == 'B' and palpite_B == real_B):
            pontos += 5 
            
    # 4. Acertou o Placar do Perdedor (Pontuação Mínima: Ex: 2 pts)
    if (vencedor_real == 'A' and palpite_B == real_B) or \
       (vencedor_real == 'B' and palpite_A == real_A):
        pontos += 2

    return pontos

def calcular_bonus_artilheiros(palpites_gols, gols_reais_jogadores):
    """
    Esta função deve ser chamada apenas quando a seleção for eliminada ou campeã.
    Compara os gols previstos para cada jogador com os gols reais do torneio.
    """
    pontos_bonus = 0
    for jogador, gols_previstos in palpites_gols.items():
        if jogador in gols_reais_jogadores and gols_previstos == gols_reais_jogadores[jogador]:
            pontos_bonus += 20 # Bônus alto por acertar os gols exatos do jogador
    return pontos_bonus

# --- INTERFACE DO APLICATIVO ---
st.title("🏆 Bolão da Copa do Mundo")
st.write("Insira seus palpites de placar e artilheiros abaixo.")

st.header("⚽ Palpite do Jogo")
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Brasil")
    palpite_brasil = st.number_input("Gols do Brasil", min_value=0, step=1, key="gols_br")

with col2:
    st.markdown("<h3 style='text-align: center;'>X</h3>", unsafe_allow_html=True)

with col3:
    st.subheader("Argentina")
    palpite_argentina = st.number_input("Gols da Argentina", min_value=0, step=1, key="gols_ar")

st.header("👟 Palpite de Gols por Jogador")
st.write("Quem fará os gols do seu palpite?")
jogador_nome = st.text_input("Nome do Jogador")
jogador_gols = st.number_input("Quantidade de gols na partida", min_value=1, step=1)

if st.button("Salvar Palpite"):
    st.success("Palpite registrado com sucesso! (Nesta versão demonstração, os dados somem ao recarregar a página).")

st.divider()

st.header("📊 Simulador de Resultados (Admin)")
st.write("Simule o resultado real da partida para ver a lógica de pontuação funcionando:")
col_r1, col_r2 = st.columns(2)
real_br = col_r1.number_input("Resultado Real: Brasil", min_value=0, step=1)
real_ar = col_r2.number_input("Resultado Real: Argentina", min_value=0, step=1)

if st.button("Calcular Minha Pontuação"):
    pontuacao = calcular_pontos_partida(palpite_brasil, palpite_argentina, real_br, real_ar)
    st.info(f"Sua pontuação neste jogo seria: **{pontuacao} pontos**!")
