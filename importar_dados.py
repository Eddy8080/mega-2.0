import pandas as pd
import os
import shutil
import datetime
from database import DatabaseManager
import openpyxl
import json

# URL de um dataset público mantido pela comunidade (exemplo: repositório kelvins/Loterias-Caixa)
# Caso o arquivo local não exista, o script tentará baixar daqui.
URL_DATASET_PUBLICO = "https://raw.githubusercontent.com/kelvins/Loterias-Caixa/master/Mega-Sena/mega_sena.csv"

ARQUIVO_LOCAL = os.path.join(os.path.dirname(__file__), "mega_sena.xlsx")

def fazer_backup_excel(caminho_arquivo):
    """Cria um backup do arquivo Excel antes da importação."""
    if not os.path.exists(caminho_arquivo):
        return

    backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = os.path.basename(caminho_arquivo)
    backup_name = f"backup_excel_{timestamp}_{nome_arquivo}"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        shutil.copy2(caminho_arquivo, backup_path)
        print(f"Backup automático do arquivo criado em: {backup_path}")
    except Exception as e:
        print(f"Aviso: Falha ao criar backup do arquivo: {e}")

def importar_dados(arquivo_usuario=None, callback=None):
    print("=== Importação de Dados da Mega-Sena ===")
    
    # Backup automático antes de processar
    arquivo_alvo = arquivo_usuario if arquivo_usuario else ARQUIVO_LOCAL
    if arquivo_alvo and os.path.exists(arquivo_alvo):
        fazer_backup_excel(arquivo_alvo)

    # 1. Carregar o DataFrame (Local ou Web)
    df = None
    
    if arquivo_usuario:
        print(f"Lendo arquivo selecionado: {arquivo_usuario}")
        try:
            if arquivo_usuario.endswith('.xlsx'):
                df = pd.read_excel(arquivo_usuario)
            else:
                df = pd.read_csv(arquivo_usuario, sep=';' if ';' in open(arquivo_usuario).readline() else ',')
        except Exception as e:
            print(f"Erro ao ler arquivo selecionado: {e}")
            return
    elif os.path.exists(ARQUIVO_LOCAL):
        print(f"Arquivo local '{ARQUIVO_LOCAL}' encontrado. Lendo dados...")
        try:
            if ARQUIVO_LOCAL.endswith('.xlsx'):
                df = pd.read_excel(ARQUIVO_LOCAL)
            else:
                # Tenta ler com separador de ponto e vírgula (comum no Brasil) ou vírgula
                df = pd.read_csv(ARQUIVO_LOCAL, sep=';')
                if len(df.columns) < 2: # Se falhar, tenta vírgula
                    df = pd.read_csv(ARQUIVO_LOCAL, sep=',')
        except Exception as e:
            print(f"Erro ao ler arquivo local: {e}")
            return
    else:
        print(f"Arquivo local não encontrado. Tentando baixar de: {URL_DATASET_PUBLICO}")
        try:
            df = pd.read_csv(URL_DATASET_PUBLICO)
            # Salva uma cópia local para uso futuro
            df.to_csv(ARQUIVO_LOCAL, index=False)
            print("Download concluído e arquivo salvo localmente.")
        except Exception as e:
            print(f"Erro ao baixar dados da internet: {e}")
            print("Verifique sua conexão ou crie um arquivo 'mega_sena.csv' manualmente.")
            return

    # 2. Inicializar Banco de Dados
    db = DatabaseManager()
    
    # 3. Processar e Salvar
    print("Iniciando persistência no banco de dados SQLite...")
    total_registros = 0

    # Normalizar nomes das colunas (Inicial)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Tratamento para cabeçalhos deslocados ou inexistentes (ex: Unnamed)
    # Executado ANTES de verificar o tipo de arquivo para garantir leitura correta
    if any("unnamed" in c for c in df.columns):
        print("Aviso: Colunas 'Unnamed' detectadas. Tentando identificar estrutura...")
        header_found = False
        
        # 1. Tenta encontrar linha de cabeçalho nas primeiras linhas
        for i, row in df.head(20).iterrows():
            row_vals = [str(v).lower() for v in row.values]
            # Procura palavras-chave (Estatísticas OU Histórico Bruto)
            if (any("posi" in v for v in row_vals) and any("dezen" in v for v in row_vals)) or \
               (any("concurso" in v for v in row_vals) or sum(1 for v in row_vals if "bola" in v or "dezen" in v) >= 6):
                
                print(f"Cabeçalho encontrado na linha {i}. Ajustando...")
                df.columns = [str(v).strip().lower().replace(' ', '_') for v in row.values]
                df = df.iloc[i+1:].reset_index(drop=True)
                header_found = True
                break
        
        # 2. Se não achou cabeçalho, tenta inferir pela quantidade de colunas (apenas para histórico bruto)
        if not header_found and len(df.columns) == 6:
            print("Estrutura de 6 colunas detectada. Assumindo formato: [Dezena1 ... Dezena6]")
            df.columns = ['dezena1', 'dezena2', 'dezena3', 'dezena4', 'dezena5', 'dezena6']

    # Verificar se é o arquivo de ESTATÍSTICAS (Ranking)
    # Colunas esperadas (aproximadas): posicao, dezena, ocorrencias, numeros que menos aparecem
    colunas_presentes = " ".join(df.columns)
    if "posi" in colunas_presentes and "dezen" in colunas_presentes and "ocorr" in colunas_presentes:
        print("Detecção: Arquivo de Estatísticas/Ranking identificado.")
        
        # Converter o DataFrame inteiro para JSON para salvar como "memória"
        # Isso permite que colunas novas sejam adicionadas sem quebrar o banco
        dados_estatisticos = df.to_json(orient="records")
        
        try:
            db.salvar_estatistica("ranking_20_anos", dados_estatisticos)
            print("Estatísticas de ranking importadas e memorizadas com sucesso!")
            
            if callback:
                callback(100, 100) # Progresso completo
            return

        except Exception as e:
            print(f"Erro ao salvar estatísticas: {e}")
            return

    # --- Se não for estatística, segue lógica de histórico de sorteios ---
    print("Detecção: Tentando processar como histórico de sorteios...")
    
    # Normalizar nomes das colunas para facilitar o acesso (Garante formato snake_case)
    df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

    total_linhas = len(df)

    # Identificar colunas de dezenas dinamicamente
    colunas_dezenas = []
    for col in df.columns:
        if 'dezena' in col or 'bola' in col:
            # Tenta verificar se é uma coluna de dezena (1 a 6)
            # Ex: dezena1, dezena_1, bola_1, etc.
            # Ignora colunas de estatística como "dezena_mais_frequente" se não for o foco
            if any(char.isdigit() for char in col): 
                colunas_dezenas.append(col)
    
    # Ordena para garantir dezena1, dezena2...
    colunas_dezenas.sort()
    
    # Se encontrou mais de 6, tenta pegar as 6 primeiras que parecem ser do sorteio
    if len(colunas_dezenas) > 6:
         # Filtra apenas as que terminam com numero 1 a 6 ou contem 1 a 6 isolado
         colunas_dezenas = [c for c in colunas_dezenas if any(c.endswith(str(i)) or f"_{i}" in c for i in range(1, 7))][:6]

    if len(colunas_dezenas) < 6:
        print("Aviso: Não foi possível identificar automaticamente as 6 colunas de dezenas.")
        print(f"Colunas encontradas: {df.columns.tolist()}")
        # Tenta fallback para nomes padrao se nao achou
        colunas_dezenas = ['dezena1', 'dezena2', 'dezena3', 'dezena4', 'dezena5', 'dezena6']

    for index, row in df.iterrows():
        try:
            # Tenta pegar concurso e data, ou gera sequencial se for apenas lista de jogos
            concurso = int(row.get('concurso', index + 1))
            data = str(row.get('data_sorteio', 'Desconhecida'))
            
            # Coleta as 6 dezenas
            dezenas = [int(row[c]) for c in colunas_dezenas]
            
            db.salvar_sorteio(concurso, data, dezenas)
            total_registros += 1
            
            if callback:
                callback(index + 1, total_linhas)

        except KeyError as e:
            print(f"Erro de coluna no CSV (formato inesperado): {e}")
            break
        except Exception as e:
            print(f"Erro ao salvar concurso {row.get('concurso', 'desconhecido')}: {e}")

    print(f"Importação finalizada! {total_registros} sorteios processados.")

if __name__ == "__main__":
    importar_dados()