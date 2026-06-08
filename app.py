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
                    "data_hora": hora_jogo.strftime("%Y-%m-%d %H:%M")
                }
                ref_jogos.document(jogo["id"]).set(jogo)
                id_jogo += 1
