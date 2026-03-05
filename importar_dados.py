import pandas as pd
import os
import shutil
import datetime
from database import DatabaseManager
import openpyxl
import json

URL_DATASET_PUBLICO = "https://raw.githubusercontent.com/kelvins/Loterias-Caixa/master/Mega-Sena/mega_sena.csv"
ARQUIVO_LOCAL = os.path.join(os.path.dirname(__file__), "mega_sena.xlsx")

def atualizar_excel_ranking():
    """
    Recalcula as estatísticas e gera o mega_sena.xlsx no padrão solicitado (Ranking Hacking).
    """
    print("ETL: Atualizando mega_sena.xlsx no padrão de Hacking...")
    db = DatabaseManager()
    todos = db.obter_todos_sorteios()
    
    if not todos:
        print(" >> Aviso: Sem dados para processar o Excel.")
        return

    # 1. Cálculos de Frequência
    freq = {i: 0 for i in range(1, 61)}
    for s in todos:
        for num in s[1:]: freq[num] += 1
    
    ranking_frequencia = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    menos_aparecem = sorted(freq.items(), key=lambda x: x[1])

    # 2. Cálculos de Atrasos
    atrasos = {}
    vistos = set()
    ultimo_conc = todos[0][0]
    for s in todos:
        for n in s[1:]:
            if n not in vistos:
                atrasos[n] = ultimo_conc - s[0]
                vistos.add(n)
        if len(vistos) == 60: break
    for i in range(1, 61):
        if i not in atrasos: atrasos[i] = ultimo_conc # Nunca saiu

    mais_atrasadas = sorted(atrasos.items(), key=lambda x: x[1], reverse=True)

    # 3. Dezenas que não aparecem (Ausentes no histórico total)
    ausentes = [n for n, f in freq.items() if f == 0]

    # 4. Montar a Tabela Final
    dados_final = []
    for i in range(60):
        linha = {
            'Posição': f"{i+1}º",
            'Dezena': ranking_frequencia[i][0],
            'Ocorrências (Aprox.)': f"{ranking_frequencia[i][1]} vezes",
            'Dezenas que não aparecem no globo do sorteio': ausentes[i] if i < len(ausentes) else "",
            'Números que menos aparecem': menos_aparecem[i][0],
            'Mais atrasadas': mais_atrasadas[i][0]
        }
        dados_final.append(linha)

    df = pd.DataFrame(dados_final)
    try:
        df.to_excel(ARQUIVO_LOCAL, index=False, engine='openpyxl')
        db.salvar_estatistica("ranking_20_anos", df.to_json(orient="records"))
        print(f" >> Sucesso: '{ARQUIVO_LOCAL}' atualizado com padrão de hacking!")
    except Exception as e:
        print(f" >> Erro ao gravar Excel: {e}")

def importar_dados(arquivo_usuario=None, callback=None):
    """Importação inicial de dados."""
    df = None
    if arquivo_usuario and os.path.exists(arquivo_usuario):
        if arquivo_usuario.endswith('.xlsx'): df = pd.read_excel(arquivo_usuario)
        else: df = pd.read_csv(arquivo_usuario)
    elif os.path.exists(ARQUIVO_LOCAL):
        df = pd.read_excel(ARQUIVO_LOCAL)
    else:
        df = pd.read_csv(URL_DATASET_PUBLICO)

    if df is None: return
    db = DatabaseManager()
    total = 0; rows = len(df)
    
    # Se for o Excel de Hacking, apenas memoriza estatísticas
    if "Posição" in str(df.columns):
        db.salvar_estatistica("ranking_20_anos", df.to_json(orient="records"))
        return

    # Se for histórico bruto, salva sorteios
    for i, row in df.iterrows():
        try:
            vals = [int(v) for v in row.values if str(v).isdigit() and 1 <= int(v) <= 60]
            if len(vals) >= 6:
                db.salvar_sorteio(i+1, "01/01/2026", vals[:6])
                total += 1
            if callback: callback(i, rows)
        except: continue
    print(f"Importação concluída: {total} sorteios.")
