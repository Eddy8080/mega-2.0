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
    Recalcula as estatísticas e gera o mega_sena.xlsx com múltiplas tabelas (sheets).
    """
    print("ETL: Atualizando mega_sena.xlsx com múltiplas tabelas...")
    db = DatabaseManager()
    todos = db.obter_todos_sorteios()
    
    if not todos:
        print(" >> Aviso: Sem dados para processar o Excel.")
        return

    # 1. Ranking de Frequência
    freq = {i: 0 for i in range(1, 61)}
    for s in todos:
        for num in s[1:]: freq[num] += 1
    
    ranking_frequencia = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    menos_aparecem = sorted(freq.items(), key=lambda x: x[1])

    # 2. Atrasos
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
        if i not in atrasos: atrasos[i] = ultimo_conc

    mais_atrasadas = sorted(atrasos.items(), key=lambda x: x[1], reverse=True)

    # 3. Dezenas Ausentes (Frequência Zero)
    ausentes = [n for n, f in freq.items() if f == 0]

    # --- TABELA 1: RANKING GERAL (Padrão Hacking) ---
    dados_hacking = []
    for i in range(60):
        linha = {
            'Posição': f"{i+1}º",
            'Dezena': ranking_frequencia[i][0],
            'Ocorrências': ranking_frequencia[i][1],
            'Ausentes (Zero Ocorr.)': ausentes[i] if i < len(ausentes) else "",
            'Menos Frequentes': menos_aparecem[i][0],
            'Mais Atrasadas': mais_atrasadas[i][0]
        }
        dados_hacking.append(linha)
    
    df_ranking = pd.DataFrame(dados_hacking)

    # --- TABELA 2: ANÁLISE PARIDADE ---
    pares = sum(1 for n in range(1,61) if n % 2 == 0)
    impares = 60 - pares
    # Estatística real dos sorteios
    total_pares = 0
    total_impares = 0
    for s in todos:
        for n in s[1:]:
            if n % 2 == 0: total_pares += 1
            else: total_impares += 1
    
    df_paridade = pd.DataFrame([
        {'Tipo': 'Pares', 'Total Ocorrências': total_pares, 'Percentual': f"{(total_pares/(6*len(todos))*100):.2f}%"},
        {'Tipo': 'Ímpares', 'Total Ocorrências': total_impares, 'Percentual': f"{(total_impares/(6*len(todos))*100):.2f}%"}
    ])

    # --- TABELA 3: QUADRANTES ---
    # Q1: 1-5, 11-15... | Q2: 6-10, 16-20... (Simplificado: 1-30 vs 31-60 e metades)
    quadrantes = {1:0, 2:0, 3:0, 4:0}
    for s in todos:
        for n in s[1:]:
            col = (n-1) % 10
            row = (n-1) // 10
            if row < 3: # Linhas 1-3
                if col < 5: quadrantes[1] += 1
                else: quadrantes[2] += 1
            else: # Linhas 4-6
                if col < 5: quadrantes[3] += 1
                else: quadrantes[4] += 1
    
    df_quadrantes = pd.DataFrame([
        {'Quadrante': 'Q1 (Top-Left)', 'Ocorrências': quadrantes[1]},
        {'Quadrante': 'Q2 (Top-Right)', 'Ocorrências': quadrantes[2]},
        {'Quadrante': 'Q3 (Bottom-Left)', 'Ocorrências': quadrantes[3]},
        {'Quadrante': 'Q4 (Bottom-Right)', 'Ocorrências': quadrantes[4]},
    ])

    # --- TABELA 4: HISTÓRICO COMPLETO ---
    dados_historico = []
    for s in todos:
        dados_historico.append({
            'Concurso': s[0],
            'Dezenas': f"{s[1]}, {s[2]}, {s[3]}, {s[4]}, {s[5]}, {s[6]}"
        })
    df_historico = pd.DataFrame(dados_historico)

    try:
        with pd.ExcelWriter(ARQUIVO_LOCAL, engine='openpyxl') as writer:
            df_ranking.to_excel(writer, sheet_name='Ranking Hacking', index=False)
            df_paridade.to_excel(writer, sheet_name='Análise Paridade', index=False)
            df_quadrantes.to_excel(writer, sheet_name='Análise Quadrantes', index=False)
            df_historico.to_excel(writer, sheet_name='Histórico Completo', index=False)
        
        db.salvar_estatistica("ranking_20_anos", df_ranking.to_json(orient="records"))
        print(f" >> Sucesso: '{ARQUIVO_LOCAL}' atualizado com múltiplas abas!")
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
    data_atual = datetime.datetime.now().strftime("%d/%m/%Y")
    for i, row in df.iterrows():
        try:
            # Tenta encontrar números válidos da Mega-Sena (1-60)
            vals = [int(v) for v in row.values if str(v).isdigit() and 1 <= int(v) <= 60]
            
            # Tenta extrair concurso e data se as colunas forem identificáveis
            concurso = i + 1
            data_sorteio = data_atual
            
            # Se a primeira coluna for um número grande (> 60), provavelmente é o concurso
            primeira_celula = str(row.iloc[0])
            if primeira_celula.isdigit():
                val_primeira = int(primeira_celula)
                if val_primeira > 60: concurso = val_primeira
            
            if len(vals) >= 6:
                # Se pegou o concurso da primeira coluna, remove dos números do sorteio se ele estiver lá
                dezenas = vals[:6]
                db.salvar_sorteio(concurso, data_sorteio, dezenas)
                total += 1
            
            if callback: callback(i, rows)
        except Exception as e:
            continue
    print(f"Importação concluída: {total} sorteios.")
    # NOVO GATILHO: Após importar para o banco, atualiza o arquivo Excel físico
    atualizar_excel_ranking()
