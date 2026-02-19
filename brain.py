import numpy as np
try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
import json
import datetime
import os
import shutil
import math
import matplotlib.pyplot as plt
import time
import io
from itertools import combinations
try:
    import cupy as cp
    HAS_CUPY = True
except (ImportError, ModuleNotFoundError):
    HAS_CUPY = False

try:
    import jax
    import jax.numpy as jnp
    HAS_JAX = True
except (ImportError, ModuleNotFoundError):
    HAS_JAX = False

from database import DatabaseManager
from importar_dados import importar_dados


class Brain:
    """
    Classe responsável pela inteligência do sistema (IA Local + Generativa).
    """

    def __init__(self, api_token=None, api_delay=2):
        self.api_token = api_token
        self.api_delay = api_delay
        # Inicialização do gerenciador de banco de dados
        self.db_manager = DatabaseManager()

        # Verifica se o banco está vazio e importa dados automaticamente
        if not self.db_manager.obter_ultimo_sorteio():
            print("Brain: Banco de dados vazio detectado.")
            print("Brain: Iniciando importação automática de dados...")
            importar_dados()

        self.quota_file = os.path.join(os.path.dirname(__file__), 'quota.json')
        self.ia_disponivel = False
        self._configurar_ia()
        print("Brain: Banco de dados conectado e inicializado.")

    def atualizar_base_dados(self, arquivo=None, callback=None):
        """Executa a rotina de importação de dados (CSV ou Excel)."""
        importar_dados(arquivo, callback)

    def _configurar_ia(self):
        """Configura o cliente do Google Gemini se o token for válido."""
        if not HAS_GENAI:
            print(
                "Brain: Biblioteca 'google-genai' não instalada. Funcionalidades de IA desativadas.")
            self.ia_disponivel = False
            return

        if self.api_token and self.api_token != "INSIRA_SEU_TOKEN_AQUI":
            try:
                self.client = genai.Client(api_key=self.api_token)
                self.ia_disponivel = True
                print("Brain: IA Generativa (Gemini) configurada com sucesso.")
            except Exception as e:
                print(f"Brain: Erro ao configurar IA Generativa: {e}")
                self.ia_disponivel = False

    def _gerenciar_cota_diaria(self):
        """
        Gerencia o contador de 1500 tokens diários.
        Retorna (Permitido: bool, Mensagem: str)
        """
        hoje = datetime.date.today().isoformat()
        dados = {"data": hoje, "uso": 0}

        # Carrega ou cria o arquivo de cota
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, 'r') as f:
                    dados_lidos = json.load(f)
                    # Se a data salva for de hoje, usa os dados; senão, reseta (novo dia)
                    if dados_lidos.get("data") == hoje:
                        dados = dados_lidos
            except (json.JSONDecodeError, ValueError):
                pass  # Arquivo corrompido ou vazio, inicia novo dia

        # Verifica limite
        if dados["uso"] >= 1500:
            return False, f"Limite diário de IA atingido (1500/1500). Renovação em: {hoje} (Amanhã)"

        # Incrementa e salva
        dados["uso"] += 1
        try:
            with open(self.quota_file, 'w') as f:
                json.dump(dados, f)
        except IOError as e:
            print(f"Brain: Erro ao salvar cota: {e}")
            # Não bloqueia o uso se falhar ao salvar, mas avisa

        return True, f"Uso da IA autorizado. ({dados['uso']}/1500)"

    def obter_cota_atual(self):
        """Retorna o uso atual e o limite diário."""
        hoje = datetime.date.today().isoformat()
        dados = {"data": hoje, "uso": 0}
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, 'r') as f:
                    dados_lidos = json.load(f)
                    if dados_lidos.get("data") == hoje:
                        dados = dados_lidos
            except:
                pass
        return dados["uso"], 1500

    def obter_status_ia(self):
        """Retorna o status da conexão com a IA (online, limitado, offline)."""
        if not self.ia_disponivel:
            return "offline", "IA Offline"
        uso, limite = self.obter_cota_atual()
        if uso >= limite:
            return "limitado", "Cota Cheia"
        return "online", "IA Online"

    def testar_conexao_api(self):
        """Testa a conexão real com a API (Ping) ignorando cota local."""
        print("Brain: Executando Ping de diagnóstico na API...")
        if not self.ia_disponivel:
            return "offline", "IA Desativada"
        
        try:
            # Tenta uma geração mínima para validar token e conectividade
            self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents="Ping"
            )
            return "online", "Conexão OK"
        except Exception as e:
            print(f"Brain: Erro no Ping: {e}")
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                return "limitado", "Erro 429 (API)"
            return "offline", "Erro Conexão"

    def coletar_estatisticas_globais(self):
        """Coleta estatísticas consolidadas para o prompt da IA."""
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            return None
        
        total = len(todos)
        
        # Frequência e Atrasos
        freq = {i: 0 for i in range(1, 61)}
        atrasos = {}
        ultimo_concurso = todos[0][0]
        encontrados = set()
        
        soma_total = 0
        pares_total = 0
        primos_total = 0
        fib_total = 0
        mult3_total = 0
        
        primos = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59}
        fibonacci = {1, 2, 3, 5, 8, 13, 21, 34, 55}
        
        for sorteio in todos:
            concurso = sorteio[0]
            dezenas = sorteio[1:]
            soma_total += sum(dezenas)
            
            for num in dezenas:
                freq[num] += 1
                if num not in encontrados:
                    atrasos[num] = ultimo_concurso - concurso
                    encontrados.add(num)
                
                if num % 2 == 0: pares_total += 1
                if num in primos: primos_total += 1
                if num in fibonacci: fib_total += 1
                if num % 3 == 0: mult3_total += 1
        
        top_quentes = [n for n, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:15]]
        top_frias = [n for n, _ in sorted(atrasos.items(), key=lambda x: x[1], reverse=True)[:15]]
        
        return {
            'total_sorteios': total,
            'top_quentes': top_quentes,
            'top_frias': top_frias,
            'media_pares': f"{pares_total/total:.2f}",
            'media_primos': f"{primos_total/total:.2f}",
            'media_soma': f"{soma_total/total:.2f}",
            'media_fibonacci': f"{fib_total/total:.2f}",
            'media_mult3': f"{mult3_total/total:.2f}"
        }

    def pensar_jogos(self):
        """
        Gera uma aposta inteligente (Híbrida: IA + Estatística + Memória).
        """
        print("Brain: Iniciando geração de jogo inteligente (Híbrido)...")
        
        stats = self.coletar_estatisticas_globais()
        prompt = ""

        if stats:
            # 2. Consulta Memória de Conhecimento (IA Local)
            # Tenta buscar se já aprendemos algo sobre "melhor estratégia"
            conhecimento_previo = self.db_manager.buscar_memoria("qual a melhor estratégia matemática para a mega sena?")
            contexto_extra = ""
            if conhecimento_previo:
                 contexto_extra = f"Use este conhecimento aprendido anteriormente: {conhecimento_previo}\n"

            # 3. Construção do Prompt para IA Generativa
            prompt = (
                f"Atue como um matemático especialista em probabilidades e loterias. "
                f"Gere um palpite de 6 números para a Mega-Sena seguindo rigorosamente a lógica matemática.\n"
                f"Base de dados histórica ({stats['total_sorteios']} concursos):\n"
                f"- Números mais frequentes (Quentes): {stats['top_quentes']}\n"
                f"- Números mais atrasados (Frias): {stats['top_frias']}\n"
                f"- Média de Pares por jogo: {stats['media_pares']} (Ideal: 3)\n"
                f"- Média de Primos por jogo: {stats['media_primos']}\n"
                f"- Média da Soma das Dezenas: {stats['media_soma']}\n"
                f"- Média de Fibonacci: {stats['media_fibonacci']}\n"
                f"- Média de Múltiplos de 3: {stats['media_mult3']}\n"
                f"{contexto_extra}"
                f"Diretrizes:\n"
                f"1. Aplique a Lei dos Grandes Números para equilibrar quentes e frias.\n"
                f"2. Mantenha equilíbrio de Pares/Ímpares e distribuição espacial (quadrantes).\n"
                f"3. Considere a temperatura (soma) próxima da média histórica.\n"
                f"4. Evite vícios humanos (datas, sequências óbvias).\n"
                f"Saída:\n"
                f"- Os 6 números sugeridos.\n"
                f"- Justificativa técnica baseada nos dados."
            )
        else:
            print(" >> Histórico bruto não encontrado. Tentando usar Ranking Importado...")
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT dado FROM estatisticas_importadas WHERE tipo='ranking_20_anos' ORDER BY data_importacao DESC LIMIT 1")
                    row = cursor.fetchone()
                
                if row:
                    print(" >> Usando estatísticas importadas (Ranking 20 anos)...")
                    dados = json.loads(row[0])
                    quentes = []
                    frias = []
                    for item in dados:
                        if 'dezena' in item and item['dezena']:
                            try: quentes.append(int(item['dezena']))
                            except: pass
                        for k in item.keys():
                            if 'menos' in k or 'não' in k:
                                try: frias.append(int(item[k]))
                                except: pass
                    
                    quentes = quentes[:15]
                    frias = frias[:15]
                    stats = {'top_quentes': quentes, 'top_frias': frias}
                    
                    prompt = (
                        f"Atue como um matemático especialista em probabilidades e loterias. "
                        f"Gere um palpite de 6 números para a Mega-Sena.\n"
                        f"Base de dados (Ranking Importado):\n"
                        f"- Números mais frequentes (Quentes): {quentes}\n"
                        f"- Números menos frequentes (Frios): {frias}\n"
                        f"Diretrizes:\n"
                        f"1. Equilibre números quentes e frios.\n"
                        f"2. Mantenha equilíbrio de Pares/Ímpares.\n"
                        f"Saída:\n"
                        f"- Os 6 números sugeridos.\n"
                        f"- Justificativa técnica."
                    )
                else:
                    print(" >> Erro: Base de dados vazia e nenhum ranking importado encontrado.")
                    print(" >> Importe 'mega_sena.xlsx' (Base ou Ranking) primeiro.")
                    return
            except Exception as e:
                print(f" >> Erro ao ler estatísticas importadas: {e}")
                return

        # 4. Execução Híbrida
        sugestao_final = None
        if self.ia_disponivel:
            print(" >> Consultando IA Generativa com dados estatísticos...")
            sugestao_final = self.consultar_ia_generativa(prompt, return_text=True)
        else:
            print(" >> IA Generativa indisponível. Usando algoritmo local ponderado.")
            # Fallback: 3 Quentes, 2 Frias, 1 Aleatório
            sugestao = []
            quentes = stats.get('top_quentes', [])
            frias = stats.get('top_frias', [])
            
            if len(quentes) >= 3 and len(frias) >= 2:
                sugestao.extend(np.random.choice(quentes, 3, replace=False))
                sugestao.extend(np.random.choice(frias, 2, replace=False))
                restantes = list(set(range(1, 61)) - set(sugestao))
                sugestao.append(np.random.choice(restantes, 1)[0])
                sugestao.sort()
                sugestao_final = f"Sugestão (Algoritmo Local): {sugestao}\nLógica: 3 números quentes, 2 frios e 1 aleatório (equilíbrio estatístico)."
                print(f" >> {sugestao_final}")
            else:
                 print(" >> Dados insuficientes para algoritmo local.")
        
        if sugestao_final:
            self.salvar_sugestao_arquivo(sugestao_final)

    def consultar_ia_generativa(self, prompt_contexto, return_text=False):
        """Consulta a IA Generativa respeitando a cota diária."""
        if not self.ia_disponivel:
            print(" >> IA Generativa não disponível (Token não configurado).")
            return

        permitido, msg = self._gerenciar_cota_diaria()
        print(f"Brain: {msg}")

        if not permitido:
            return

        # Pausa de segurança para evitar Rate Limit (429)
        print(f"Brain: Aguardando {self.api_delay} segundos para respeitar limites da API...")
        time.sleep(self.api_delay)

        try:
            print("Brain: Consultando Gemini para análise avançada...")
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt_contexto
            )
            print(f" >> Resposta da IA:\n{response.text}")
            if return_text:
                return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(" >> Erro: Cota da API excedida (429). Tente novamente mais tarde.")
            else:
                print(f" >> Erro na comunicação com a IA: {e}")

    def conferir_resultado(self, aposta_usuario=None):
        """Confere uma aposta (usuário ou fixa) contra o último sorteio."""
        print("Brain: Buscando último sorteio na base de dados...")
        ultimo = self.db_manager.obter_ultimo_sorteio()

        if not ultimo:
            print(" >> Erro: Base de dados vazia. Execute a importação primeiro.")
            return

        sorteados = np.array(ultimo['numeros'])
        print(f" >> Último Concurso: {ultimo['concurso']} ({ultimo['data']})")
        print(f" >> Dezenas Sorteadas: {sorteados}")

        # Define a aposta a ser conferida
        if aposta_usuario:
            aposta = np.array(aposta_usuario)
            print(f" >> Aposta do Usuário: {aposta}")
        else:
            aposta = np.array([4, 11, 25, 33, 42, 55])
            print(f" >> Aposta Fixa (Exemplo): {aposta}")

        # Verifica acertos
        acertos = np.intersect1d(sorteados, aposta)
        qtd = len(acertos)

        print(f" >> Acertos: {qtd} {acertos if qtd > 0 else ''}")

        if qtd == 6:
            print(" >> RESULTADO: SENA! (Parabéns!)")
        elif qtd == 5:
            print(" >> RESULTADO: QUINA!")
        elif qtd == 4:
            print(" >> RESULTADO: QUADRA!")
        else:
            print(" >> RESULTADO: Não premiado.")

    def analisar_atrasos(self):
        """Analisa quais números estão há mais tempo sem sair (dezenas frias)."""
        print("Brain: Analisando atrasos...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia. Execute a importação primeiro.")
            return

        concurso_atual = todos[0][0]
        atrasos = {}
        numeros_encontrados = set()

        # Percorre do sorteio mais recente para o mais antigo
        for sorteio in todos:
            concurso = sorteio[0]
            dezenas = sorteio[1:]  # bola1 a bola6

            for num in dezenas:
                if num not in numeros_encontrados:
                    atrasos[num] = concurso_atual - concurso
                    numeros_encontrados.add(num)

            if len(numeros_encontrados) == 60:
                break

        # Ordena decrescente pelo tempo de atraso
        ranking = sorted(atrasos.items(), key=lambda x: x[1], reverse=True)

        print(f" >> Top 10 Dezenas mais atrasadas (Frias):")
        for num, atraso in ranking[:10]:
            print(f"    Dezena {num:02d}: {atraso} concursos sem sair")

    def analisar_pares_impares(self):
        """Analisa a proporção de números pares e ímpares nos sorteios."""
        print("Brain: Analisando proporção Par/Ímpar...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia. Execute a importação primeiro.")
            return

        total_sorteios = len(todos)
        # Dicionário para contar padrões: ex: "3P-3I", "4P-2I"
        padroes = {
            "0P-6I": 0, "1P-5I": 0, "2P-4I": 0, "3P-3I": 0,
            "4P-2I": 0, "5P-1I": 0, "6P-0I": 0
        }

        for sorteio in todos:
            dezenas = sorteio[1:]
            pares = sum(1 for num in dezenas if num % 2 == 0)
            impares = 6 - pares
            chave = f"{pares}P-{impares}I"
            if chave in padroes:
                padroes[chave] += 1

        print(f" >> Estatística Par/Ímpar em {total_sorteios} concursos:")

        # Ordenar por frequência
        ranking = sorted(padroes.items(), key=lambda x: x[1], reverse=True)

        for padrao, qtd in ranking:
            porcentagem = (qtd / total_sorteios) * 100
            print(f"    {padrao}: {qtd} vezes ({porcentagem:.2f}%)")

    def analisar_ia_repeticoes(self):
        """Usa a IA para analisar repetições de jogos nos últimos 20 anos."""
        prompt = (
            "Analise a sequência de jogos e padrões que mais se repetem nos últimos vinte anos "
            "na Mega-Sena. Com base nessa análise histórica, me dê uma dica de aposta ou "
            "sugira uma combinação de números fundamentada."
        )
        self.consultar_ia_generativa(prompt)

    def analisar_quadrantes(self):
        """Analisa a distribuição dos números nos 4 quadrantes."""
        print("Brain: Analisando distribuição por quadrantes...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia. Execute a importação primeiro.")
            return

        total_sorteios = len(todos)
        # Q1: 01-05, 11-15, 21-25 (Sup. Esq)
        # Q2: 06-10, 16-20, 26-30 (Sup. Dir)
        # Q3: 31-35, 41-45, 51-55 (Inf. Esq)
        # Q4: 36-40, 46-50, 56-60 (Inf. Dir)

        padroes_quadrantes = {}

        for sorteio in todos:
            dezenas = sorteio[1:]
            q_counts = [0, 0, 0, 0]  # Q1, Q2, Q3, Q4

            for num in dezenas:
                col = num % 10
                is_left = (col >= 1 and col <= 5)

                if num <= 30:
                    idx = 0 if is_left else 1  # Q1 ou Q2
                else:
                    idx = 2 if is_left else 3  # Q3 ou Q4
                q_counts[idx] += 1

            chave = f"{q_counts[0]}-{q_counts[1]}-{q_counts[2]}-{q_counts[3]}"
            padroes_quadrantes[chave] = padroes_quadrantes.get(chave, 0) + 1

        print(
            f" >> Distribuição por Quadrantes (Q1-Q2-Q3-Q4) em {total_sorteios} concursos:")
        print("    (Legenda: Q1=Sup.Esq, Q2=Sup.Dir, Q3=Inf.Esq, Q4=Inf.Dir)")

        ranking = sorted(padroes_quadrantes.items(),
                         key=lambda x: x[1], reverse=True)

        for padrao, qtd in ranking[:10]:  # Top 10 padrões
            porcentagem = (qtd / total_sorteios) * 100
            print(f"    {padrao}: {qtd} vezes ({porcentagem:.2f}%)")

    def explicar_desdobramento(self):
        """Usa a IA para explicar Desdobramento e sugerir estratégia econômica."""
        prompt = (
            "Explique o conceito de 'Desdobramento' na Mega-Sena de forma didática. "
            "Dê exemplos práticos de como isso aumenta as chances de ganhar e "
            "sugira uma estratégia econômica de desdobramento para apostadores com orçamento limitado."
        )
        self.consultar_ia_generativa(prompt)

    def analisar_linhas_colunas(self):
        """Analisa a frequência de sorteio por Linhas e Colunas."""
        print("Brain: Analisando Linhas e Colunas...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia. Execute a importação primeiro.")
            return

        total_sorteios = len(todos)

        # Inicializa contadores
        linhas = {i: 0 for i in range(1, 7)}  # Linhas 1 a 6
        colunas = {i: 0 for i in range(1, 11)}  # Colunas 1 a 10

        for sorteio in todos:
            dezenas = sorteio[1:]
            for num in dezenas:
                # Linha: (num - 1) // 10 + 1
                linha = (num - 1) // 10 + 1
                linhas[linha] += 1

                # Coluna: num % 10. Se 0, é coluna 10.
                coluna = num % 10
                if coluna == 0:
                    coluna = 10
                colunas[coluna] += 1

        print(
            f" >> Análise de Linhas e Colunas em {total_sorteios} concursos:")

        print("    --- Frequência por LINHA ---")
        ranking_linhas = sorted(
            linhas.items(), key=lambda x: x[1], reverse=True)
        for lin, qtd in ranking_linhas:
            media = qtd / total_sorteios
            print(f"    Linha {lin}: {qtd} dezenas (Média: {media:.2f}/jogo)")

        print("    --- Frequência por COLUNA ---")
        ranking_colunas = sorted(
            colunas.items(), key=lambda x: x[1], reverse=True)
        for col, qtd in ranking_colunas:
            media = qtd / total_sorteios
            print(f"    Coluna {col}: {qtd} dezenas (Média: {media:.2f}/jogo)")

    def analisar_numeros_primos(self):
        """Analisa a frequência de números primos nos sorteios."""
        print("Brain: Analisando números primos...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia. Execute a importação primeiro.")
            return

        total_sorteios = len(todos)
        # Primos entre 1 e 60
        primos = {2, 3, 5, 7, 11, 13, 17, 19,
                  23, 29, 31, 37, 41, 43, 47, 53, 59}
        contagem = {i: 0 for i in range(7)}  # Contadores para 0 a 6 primos

        for sorteio in todos:
            dezenas = sorteio[1:]
            qtd = sum(1 for num in dezenas if num in primos)
            contagem[qtd] += 1

        print(
            f" >> Frequência de Números Primos em {total_sorteios} concursos:")
        for qtd, count in contagem.items():
            porcentagem = (count / total_sorteios) * 100
            print(f"    {qtd} Primos: {count} vezes ({porcentagem:.2f}%)")

    def analisar_soma_dezenas(self):
        """Analisa a soma das dezenas de cada sorteio."""
        print("Brain: Analisando soma das dezenas...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia. Execute a importação primeiro.")
            return

        total_sorteios = len(todos)
        somas = []

        # Faixas de soma para análise de frequência
        faixas = {
            "< 150": 0,
            "150 - 180": 0,
            "181 - 210": 0,
            "211 - 240": 0,
            "> 240": 0
        }

        for sorteio in todos:
            dezenas = sorteio[1:]
            soma = sum(dezenas)
            somas.append(soma)

            if soma < 150:
                faixas["< 150"] += 1
            elif 150 <= soma <= 180:
                faixas["150 - 180"] += 1
            elif 181 <= soma <= 210:
                faixas["181 - 210"] += 1
            elif 211 <= soma <= 240:
                faixas["211 - 240"] += 1
            else:
                faixas["> 240"] += 1

        media = sum(somas) / total_sorteios
        minimo = min(somas)
        maximo = max(somas)

        print(
            f" >> Estatísticas da Soma das Dezenas em {total_sorteios} concursos:")
        print(f"    Média Geral: {media:.2f}")
        print(f"    Mínimo: {minimo} | Máximo: {maximo}")
        print("    --- Distribuição por Faixas ---")

        for faixa, qtd in faixas.items():
            porcentagem = (qtd / total_sorteios) * 100
            print(f"    {faixa}: {qtd} vezes ({porcentagem:.2f}%)")

    def analisar_finais(self):
        """Analisa a frequência do último dígito (final) das dezenas."""
        print("Brain: Analisando finais das dezenas...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia. Execute a importação primeiro.")
            return

        total_sorteios = len(todos)
        finais = {i: 0 for i in range(10)}  # 0 a 9

        for sorteio in todos:
            dezenas = sorteio[1:]
            for num in dezenas:
                final = num % 10
                finais[final] += 1

        print(
            f" >> Frequência dos Finais (Último Dígito) em {total_sorteios} concursos:")

        ranking = sorted(finais.items(), key=lambda x: x[1], reverse=True)

        for final, qtd in ranking:
            media = qtd / total_sorteios
            print(f"    Final {final}: {qtd} vezes (Média: {media:.2f}/jogo)")

    def gerar_palpite_ia(self):
        """Gera um palpite usando a IA com base em estatísticas quentes/frias."""
        print("Brain: Coletando estatísticas para o Palpite do Dia...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # 1. Calcular Frequência (Quentes)
        frequencia = {i: 0 for i in range(1, 61)}
        for sorteio in todos:
            for num in sorteio[1:]:
                frequencia[num] += 1

        top_quentes = sorted(frequencia.items(),
                             key=lambda x: x[1], reverse=True)[:10]
        quentes_str = ", ".join([str(n) for n, _ in top_quentes])

        # 2. Calcular Atrasos (Frias)
        concurso_atual = todos[0][0]
        atrasos = {}
        encontrados = set()
        for sorteio in todos:
            concurso = sorteio[0]
            for num in sorteio[1:]:
                if num not in encontrados:
                    atrasos[num] = concurso_atual - concurso
                    encontrados.add(num)
            if len(encontrados) == 60:
                break

        top_frias = sorted(
            atrasos.items(), key=lambda x: x[1], reverse=True)[:10]
        frias_str = ", ".join([str(n) for n, _ in top_frias])

        # 3. Construir Prompt e Consultar IA
        prompt = (
            f"Atue como um especialista em estatística de loterias. "
            f"Com base nos dados históricos da Mega-Sena:\n"
            f"- Números mais frequentes (Quentes): [{quentes_str}]\n"
            f"- Números mais atrasados (Frios): [{frias_str}]\n"
            f"Gere um 'Palpite do Dia' contendo um jogo de 6 números. "
            f"Sua estratégia deve equilibrar números quentes e frios, e manter uma proporção "
            f"equilibrada de Pares e Ímpares. Explique brevemente a escolha."
        )
        self.consultar_ia_generativa(prompt)

    def analisar_ciclos(self):
        """Analisa os ciclos de saída de todas as 60 dezenas."""
        print("Brain: Analisando ciclos das dezenas...")
        # Obtém todos os sorteios, mas inverte para ordem cronológica (antigo -> novo)
        todos = self.db_manager.obter_todos_sorteios()[::-1]

        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        ciclos = []
        dezenas_no_ciclo = set()
        inicio_ciclo = todos[0][0]

        for sorteio in todos:
            concurso = sorteio[0]
            dezenas = sorteio[1:]

            dezenas_no_ciclo.update(dezenas)

            if len(dezenas_no_ciclo) == 60:
                tamanho = concurso - inicio_ciclo + 1
                ciclos.append((inicio_ciclo, concurso, tamanho))
                dezenas_no_ciclo = set()
                inicio_ciclo = concurso + 1

        print(
            f" >> Análise de Ciclos (Total de ciclos completos: {len(ciclos)})")
        print("    Um ciclo fecha quando todas as 60 dezenas foram sorteadas.")

        for inicio, fim, tamanho in ciclos[-5:]:  # Mostra os últimos 5 ciclos
            print(f"    Ciclo {inicio} ao {fim}: Levou {tamanho} concursos")

        # Ciclo atual (em aberto)
        if len(dezenas_no_ciclo) > 0:
            faltam = 60 - len(dezenas_no_ciclo)
            print(
                f"    >> Ciclo Atual (aberto): Faltam {faltam} dezenas para fechar.")
            print(
                f"    >> Dezenas que faltam sair neste ciclo: {sorted(list(set(range(1, 61)) - dezenas_no_ciclo))}")

    def verificar_saude_gpu(self):
        """
        Verifica explicitamente se o CuPy e o driver CUDA estão comunicando corretamente.
        Retorna True se a GPU estiver pronta para uso, False caso contrário.
        """
        if not HAS_CUPY:
            return False
        
        try:
            # Tenta uma operação mínima na GPU para validar o driver antes de rodar carga pesada
            _ = cp.array([1]) + 1
            return True
        except Exception as e:
            print(f"Brain: GPU detectada, mas inoperante (Driver/CUDA erro): {e}")
            return False

    def simular_cenarios(self, qtd_simulacoes=1_000_000):
        """
        Realiza uma Simulação de Monte Carlo.
        Gera milhões de números aleatórios para analisar tendências de curto prazo na aleatoriedade.
        """
        print(
            f"Brain: Iniciando simulação de {qtd_simulacoes} cenários futuros...")

        # Tenta usar GPU se disponível, mas prepara fallback para CPU em caso de erro de driver
        use_gpu = HAS_CUPY
        use_gpu = self.verificar_saude_gpu()
        
        while True:
            xp = cp if use_gpu else np
            device_name = "GPU (CuPy)" if use_gpu else "CPU (NumPy)"
            print(f"Brain: Utilizando processamento via {device_name}...")

            try:
                # Gera 6 milhões de números aleatórios entre 1 e 60
                # Simula o sorteio de 1 milhão de cartelas
                universo_amostral = xp.random.randint(
                    1, 61, size=qtd_simulacoes * 6)

                # Calcula a frequência de cada número (1 a 60)
                # minlength=61 garante índices de 0 a 60. Pegamos do 1 ao 60.
                frequencia = xp.bincount(universo_amostral, minlength=61)[1:]

                # Encontra os 6 números que mais apareceram nesta simulação
                indices_top = xp.argsort(frequencia)[::-1][:6]
                numeros_simulados = indices_top + 1  # Ajusta o índice (0 vira 1)

                # Converte para numpy padrão para exibição se estiver na GPU
                if use_gpu:
                    numeros_simulados = cp.asnumpy(numeros_simulados)

                print(f" >> Análise concluída.")
                print(
                    f" >> Números mais frequentes na simulação: {numeros_simulados}")
                print(" >> Nota: Isso demonstra a Lei dos Grandes Números em ação.")
                break # Sucesso, sai do loop

            except Exception as e:
                if use_gpu:
                    print(f" >> Erro ao utilizar GPU: {e}")
                    print(" >> Alternando automaticamente para CPU (NumPy)...")
                    use_gpu = False
                    continue # Tenta novamente com CPU
                else:
                    print(f"Erro crítico durante a simulação: {e}")
                    break

    def comparar_simulacao_realidade(self, qtd_simulacoes=1_000_000):
        """
        Compara os números mais frequentes da história real com uma simulação de Monte Carlo.
        Objetivo: Mostrar a diferença entre a tendência histórica e a probabilidade pura.
        """
        print(f"Brain: Iniciando comparação (Histórico vs Simulação de {qtd_simulacoes} jogos)...")

        # 1. Análise do Histórico Real
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        freq_real = {i: 0 for i in range(1, 61)}
        for sorteio in todos:
            for num in sorteio[1:]:
                freq_real[num] += 1
        
        # Top 15 Reais
        ranking_real = sorted(freq_real.items(), key=lambda x: x[1], reverse=True)[:15]
        top_real = [n for n, _ in ranking_real]

        # 2. Simulação de Monte Carlo
        use_gpu = HAS_CUPY
        use_gpu = self.verificar_saude_gpu()
        
        while True:
            xp = cp if use_gpu else np
            device = "GPU" if use_gpu else "CPU"
            print(f" >> Gerando simulação via {device}...")

            try:
                universo = xp.random.randint(1, 61, size=qtd_simulacoes * 6)
                freq_sim = xp.bincount(universo, minlength=61)[1:]
                indices_sim = xp.argsort(freq_sim)[::-1][:15]
                top_simulacao = (indices_sim + 1).tolist() # Converte para lista Python
                if use_gpu: top_simulacao = [int(x) for x in top_simulacao]

                # 3. Comparação e Exibição
                interseccao = set(top_real) & set(top_simulacao)
                
                print("\n=== Relatório Comparativo: Realidade vs Probabilidade ===")
                print(f"1. Top 15 Mais Frequentes (Histórico Real): {top_real}")
                print(f"2. Top 15 Mais Frequentes (Simulação Pura): {top_simulacao}")
                print("-" * 60)
                print(f" >> Convergência (Números em ambos): {sorted(list(interseccao))}")
                print("-" * 60)
                break
            except Exception as e:
                if use_gpu:
                    print(f" >> Erro na GPU: {e}. Alternando para CPU...")
                    use_gpu = False
                    continue
                else:
                    print(f" >> Erro na simulação comparativa: {e}")
                    break

    def benchmark_cpu_vs_gpu(self, qtd_simulacoes=5_000_000):
        """
        Realiza um benchmark comparando o tempo de execução entre CPU (NumPy) e GPU (CuPy).
        """
        print(f"Brain: Iniciando Benchmark com {qtd_simulacoes} simulações...")
        
        # 1. Teste CPU
        print(" >> Testando CPU (NumPy)...")
        start_cpu = time.time()
        try:
            universo = np.random.randint(1, 61, size=qtd_simulacoes * 6)
            freq = np.bincount(universo, minlength=61)[1:]
            top = np.argsort(freq)[::-1][:6]
            _ = top + 1
        except Exception as e:
            print(f"Erro no teste de CPU: {e}")
            return
        end_cpu = time.time()
        tempo_cpu = end_cpu - start_cpu
        print(f"    Tempo CPU: {tempo_cpu:.4f} segundos")

        # 2. Teste GPU
        tempo_gpu = None
        if self.verificar_saude_gpu():
            print(" >> Testando GPU (CuPy)...")
            start_gpu = time.time()
            try:
                universo_gpu = cp.random.randint(1, 61, size=qtd_simulacoes * 6)
                freq_gpu = cp.bincount(universo_gpu, minlength=61)[1:]
                top_gpu = cp.argsort(freq_gpu)[::-1][:6]
                res_gpu = top_gpu + 1
                _ = cp.asnumpy(res_gpu) # Força sincronização/transferência
            except Exception as e:
                print(f"Erro no teste de GPU: {e}")
            else:
                end_gpu = time.time()
                tempo_gpu = end_gpu - start_gpu
                print(f"    Tempo GPU: {tempo_gpu:.4f} segundos")
        else:
            print(" >> GPU não disponível ou driver incompatível para teste.")

        # 3. Resultados
        print("\n=== Resultado do Benchmark ===")
        print(f"CPU: {tempo_cpu:.4f}s")
        if tempo_gpu:
            print(f"GPU: {tempo_gpu:.4f}s")
            if tempo_gpu < tempo_cpu:
                speedup = tempo_cpu / tempo_gpu
                print(f" >> A GPU foi {speedup:.2f}x mais rápida que a CPU.")
            else:
                print(" >> A CPU foi mais rápida (cenário pequeno ou overhead de transferência).")
        else:
            print("GPU: N/A")
        print("-" * 30)

    def exemplo_gpu(self):
        """
        Demonstração de uso de arrays na GPU com CuPy e JAX.
        """
        print("Brain: Iniciando exemplo de processamento em GPU...")
        try:
            # Exemplo com CuPy (Cálculo de array na GPU)
            if HAS_CUPY:
                print("  - CuPy: Criando array e realizando operação...")
                x_gpu = cp.arange(10).reshape(2, 5)
                y_gpu = x_gpu ** 2
                print(f"    Resultado CuPy:\n{y_gpu}")
            else:
                print("  - CuPy: Biblioteca não disponível ou não configurada.")

            # Exemplo com JAX (Cálculo JIT)
            if HAS_JAX:
                print("  - JAX: Criando matriz aleatória...")
                key = jax.random.PRNGKey(42)
                matriz_jax = jax.random.normal(key, (5, 5))
                print(f"    Shape JAX: {matriz_jax.shape}")
            else:
                print("  - JAX: Biblioteca não disponível ou não configurada.")

        except Exception as e:
            print(f"Erro ao executar na GPU: {e}")

    def fazer_backup(self):
        """Cria uma cópia de segurança do banco de dados."""
        print("Brain: Iniciando backup do banco de dados...")

        db_path = self.db_manager.db_path
        if not os.path.exists(db_path):
            print(" >> Erro: Banco de dados não encontrado.")
            return

        backup_dir = os.path.join(os.path.dirname(__file__), 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"mega_sena_backup_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_name)

        try:
            shutil.copy2(db_path, backup_path)
            print(f" >> Backup realizado com sucesso!")
            print(f" >> Arquivo salvo em: {backup_path}")
        except Exception as e:
            print(f" >> Erro ao criar backup: {e}")

    def restaurar_backup(self, caminho_backup):
        """Restaura um backup do banco de dados."""
        print(
            f"Brain: Iniciando restauração de: {os.path.basename(caminho_backup)}")

        if not os.path.exists(caminho_backup):
            print(" >> Erro: Arquivo de backup não encontrado.")
            return

        db_path = self.db_manager.db_path

        try:
            shutil.copy2(caminho_backup, db_path)
            print(" >> Sucesso: Banco de dados restaurado.")
            print(" >> Os dados antigos foram substituídos pelo backup selecionado.")
        except Exception as e:
            print(f" >> Erro crítico ao restaurar: {e}")

    def calcular_custo_aposta(self, quantidade_numeros):
        """Calcula o custo de uma aposta múltipla."""
        print(f"Brain: Calculando custo para {quantidade_numeros} números...")
        if not (6 <= quantidade_numeros <= 20):
            print(" >> Erro: A quantidade de números deve ser entre 6 e 20.")
            return

        # Combinação C(n, 6)
        combinacoes = math.comb(quantidade_numeros, 6)
        custo = combinacoes * 6.00  # Preço base R$ 6,00

        print(f" >> Aposta com {quantidade_numeros} números:")
        print(f"    Equivale a {combinacoes} apostas simples (senas).")
        print(f"    Custo Total: R$ {custo:,.2f}".replace(
            ",", "X").replace(".", ",").replace("X", "."))

    def analisar_sequencias(self):
        """Analisa a frequência de sequências numéricas (números consecutivos)."""
        print("Brain: Analisando sequências numéricas...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        total_sorteios = len(todos)
        # Contadores para sequências de tamanho 2 a 6
        seq_counts = {2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        sorteios_com_seq = 0

        for sorteio in todos:
            dezenas = sorted(sorteio[1:])
            current_seq_len = 1
            found_seq = False

            for i in range(len(dezenas) - 1):
                if dezenas[i+1] == dezenas[i] + 1:
                    current_seq_len += 1
                else:
                    if current_seq_len >= 2:
                        seq_counts[current_seq_len] += 1
                        found_seq = True
                    current_seq_len = 1

            # Verifica a última sequência do sorteio
            if current_seq_len >= 2:
                seq_counts[current_seq_len] += 1
                found_seq = True

            if found_seq:
                sorteios_com_seq += 1

        print(f" >> Análise de Sequências em {total_sorteios} concursos:")
        porcentagem_total = (sorteios_com_seq / total_sorteios) * 100
        print(
            f"    Sorteios com pelo menos uma sequência: {sorteios_com_seq} ({porcentagem_total:.2f}%)")

        for length in sorted(seq_counts.keys()):
            qtd = seq_counts[length]
            if qtd > 0:
                # Porcentagem em relação ao total de sorteios (nota: um sorteio pode ter mais de uma sequência)
                freq_relativa = (qtd / total_sorteios) * 100
                print(
                    f"    Sequências de {length} números (ex: 1,2...): {qtd} ocorrências ({freq_relativa:.2f}%)")

    def simular_gastos(self, orcamento):
        """Sugere combinações de apostas baseadas no orçamento do usuário."""
        print(
            f"Brain: Simulando gastos para orçamento de R$ {orcamento:.2f}...")
        if orcamento < 6.00:
            print(" >> Orçamento insuficiente. Aposta mínima custa R$ 6,00.")
            return

        # Opção 1: Volume (Jogos Simples)
        qtd_simples = int(orcamento // 6)
        troco_simples = orcamento % 6
        print(
            f" >> Estratégia 1 (Volume): Fazer {qtd_simples} jogos simples de 6 números.")
        print(
            f"    Custo: R$ {qtd_simples * 6:.2f} | Troco: R$ {troco_simples:.2f}")

        # Opção 2: Potência (Desdobramento)
        # Encontrar a aposta com mais dezenas que cabe no orçamento
        melhor_aposta_qtd = 6
        custo_melhor = 6.00

        for n in range(7, 21):
            custo = math.comb(n, 6) * 6.00
            if custo <= orcamento:
                melhor_aposta_qtd = n
                custo_melhor = custo
            else:
                break

        if melhor_aposta_qtd > 6:
            print(
                f" >> Estratégia 2 (Potência): Fazer 1 jogo de {melhor_aposta_qtd} números.")
            print(f"    Custo: R$ {custo_melhor:,.2f}".replace(
                ",", "X").replace(".", ",").replace("X", "."))

            # Verificar se sobra dinheiro para jogos simples
            sobra = orcamento - custo_melhor
            if sobra >= 6.00:
                extras = int(sobra // 6)
                print(
                    f"    + {extras} jogos simples com o troco (R$ {extras * 6:.2f}).")
                sobra = sobra % 6

            print(f"    Troco Final: R$ {sobra:.2f}")
        else:
            print(
                " >> Estratégia 2 (Potência): Seu orçamento permite apenas jogos simples (veja Estratégia 1).")

    def analisar_meses(self):
        """Analisa a frequência dos números por mês (sazonalidade)."""
        print("Brain: Analisando sazonalidade (meses)...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Estrutura: {1: {num: qtd}, 2: {num: qtd}, ... 12: {num: qtd}}
        meses = {i: {} for i in range(1, 13)}
        nomes_meses = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }

        for sorteio in todos:
            # Data formato DD/MM/AAAA
            data_str = sorteio[1]
            try:
                mes = int(data_str.split('/')[1])
                for num in sorteio[2:]: # Pula concurso e data
                    meses[mes][num] = meses[mes].get(num, 0) + 1
            except (IndexError, ValueError):
                continue # Pula datas inválidas

        print(" >> Top 3 Números mais frequentes por Mês:")
        for i in range(1, 13):
            freqs = meses[i]
            if not freqs:
                print(f"    {nomes_meses[i]}: Sem dados.")
                continue
            top3 = sorted(freqs.items(), key=lambda x: x[1], reverse=True)[:3]
            top3_str = ", ".join([f"{n}({q}x)" for n, q in top3])
            print(f"    {nomes_meses[i]}: {top3_str}")

    def gerar_grafico_frequencia(self):
        """Gera e exibe um gráfico de barras com a frequência dos números."""
        print("Brain: Gerando gráfico de frequência...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Contagem de frequência
        frequencia = {i: 0 for i in range(1, 61)}
        for sorteio in todos:
            for num in sorteio[1:]:
                frequencia[num] += 1

        # Preparar dados para o gráfico
        numeros = list(frequencia.keys())
        contagens = list(frequencia.values())

        # Configurar o gráfico
        plt.figure(figsize=(12, 6))
        plt.bar(numeros, contagens, color='skyblue', edgecolor='navy')
        plt.title('Frequência dos Números da Mega-Sena (Todos os Concursos)')
        plt.xlabel('Dezenas (1-60)')
        plt.ylabel('Quantidade de Vezes Sorteado')
        plt.xticks(range(1, 61), rotation=90, fontsize=8)
        plt.grid(axis='y', linestyle='--', alpha=0.7)

        # Destacar a média
        media = sum(contagens) / 60
        plt.axhline(y=media, color='r', linestyle='-',
                    label=f'Média ({media:.1f})')
        plt.legend()

        plt.tight_layout()
        plt.show()
        print(" >> Gráfico exibido em nova janela.")

    def gerar_heatmap_correlacao(self):
        """Gera um mapa de calor (Heatmap) mostrando a correlação entre todas as dezenas."""
        print("Brain: Gerando Heatmap de Correlação...")
        todos = self.db_manager.obter_todos_sorteios()

        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Cria uma matriz 60x60 preenchida com zeros
        matriz = np.zeros((60, 60), dtype=int)

        for sorteio in todos:
            # Ajusta para índice 0-59 (Dezena 1 vira índice 0)
            dezenas = [d - 1 for d in sorteio[1:]]
            
            # Incrementa a contagem para cada par encontrado no sorteio
            for i in range(len(dezenas)):
                for j in range(i + 1, len(dezenas)):
                    d1, d2 = dezenas[i], dezenas[j]
                    matriz[d1][d2] += 1
                    matriz[d2][d1] += 1 # Matriz simétrica

        # Configuração do Gráfico
        plt.figure(figsize=(10, 8))
        plt.imshow(matriz, cmap='hot', interpolation='nearest', origin='lower')
        plt.colorbar(label='Frequência de Ocorrência Conjunta')
        plt.title('Heatmap de Correlação entre Dezenas (1-60)')
        plt.xlabel('Dezenas (Índice)')
        plt.ylabel('Dezenas (Índice)')
        plt.tight_layout()
        plt.show()
        print(" >> Gráfico de calor exibido.")

    def interagir_hibrido(self, pergunta):
        """Interage com o usuário usando memória local + IA Generativa."""
        if not pergunta:
            return
            
        print(f"Brain: Processando pergunta: '{pergunta}'")
        
        # 1. Consulta Memória de Longo Prazo (IA Local)
        memoria = self.db_manager.buscar_memoria(pergunta)
        if memoria:
            print(f" >> [Memória Local]: Encontrei essa resposta no banco de dados.")
            print(f" >> {memoria}")
            return

        # 2. Se não sabe, pergunta para a IA Generativa (Aprendizado)
        print(f" >> [Memória Local]: Não sei a resposta. Consultando IA Generativa...")
        resposta_ia = self.consultar_ia_generativa(pergunta, return_text=True)
        
        # 3. Aprende (Salva na memória)
        if resposta_ia:
            self.db_manager.salvar_memoria(pergunta, resposta_ia)
            print(f" >> [Aprendizado]: Resposta salva na memória de longo prazo para consultas futuras.")

    def limpar_memoria_ia(self):
        """Limpa a memória de aprendizado da IA."""
        self.db_manager.limpar_memoria()
        print("Brain: Memória de longo prazo da IA foi apagada com sucesso.")

    def exportar_memoria_ia(self, caminho_arquivo):
        """Exporta a memória de aprendizado para um arquivo JSON."""
        print(f"Brain: Exportando memória para {caminho_arquivo}...")
        dados = self.db_manager.obter_toda_memoria()
        
        if not dados:
            print(" >> Memória vazia. Nada para exportar.")
            return

        memoria_dict = {pergunta: resposta for pergunta, resposta in dados}
        
        try:
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                json.dump(memoria_dict, f, indent=4, ensure_ascii=False)
            print(f" >> Sucesso: {len(memoria_dict)} itens de memória exportados.")
        except Exception as e:
            print(f" >> Erro ao exportar memória: {e}")

    def analisar_qualidade_memoria(self):
        """Analisa a qualidade das respostas salvas e sugere melhorias."""
        print("Brain: Analisando qualidade da memória de longo prazo...")
        dados = self.db_manager.obter_toda_memoria()
        
        if not dados:
            print(" >> Memória vazia.")
            return

        candidatas = []
        for pergunta, resposta in dados:
            # Critério simples: respostas com menos de 50 caracteres podem ser curtas demais
            if len(resposta) < 50:
                candidatas.append(pergunta)

        if candidatas:
            print(f" >> Encontradas {len(candidatas)} respostas potencialmente fracas (curtas).")
            print(" >> Sugestão: Re-consultar as seguintes perguntas na IA:")
            for p in candidatas:
                print(f"    - '{p}'")
        else:
            print(" >> Todas as respostas na memória parecem ter um tamanho adequado.")

    def refinar_memoria_ia(self):
        """Refina automaticamente as respostas fracas na memória."""
        print("Brain: Iniciando refinamento de memória...")
        dados = self.db_manager.obter_toda_memoria()
        
        if not dados:
            print(" >> Memória vazia.")
            return

        candidatas = []
        for pergunta, resposta in dados:
            if len(resposta) < 50:
                candidatas.append(pergunta)
        
        if not candidatas:
            print(" >> Nenhuma resposta fraca encontrada para refinar.")
            return

        print(f" >> Refinando {len(candidatas)} itens...")
        
        for i, pergunta in enumerate(candidatas):
            print(f" >> [{i+1}/{len(candidatas)}] Refinando: '{pergunta}'")
            
            # Adiciona instrução para ser mais detalhado
            prompt_refinado = f"{pergunta}\n(Por favor, forneça uma resposta detalhada e completa sobre isso.)"
            
            nova_resposta = self.consultar_ia_generativa(prompt_refinado, return_text=True)
            
            if nova_resposta:
                self.db_manager.salvar_memoria(pergunta, nova_resposta)
                print("    -> Atualizado com sucesso.")
            else:
                print("    -> Falha ao obter nova resposta.")

    def gerar_relatorio_pdf(self, caminho_arquivo):
        """Gera um relatório PDF completo com estatísticas consolidadas."""
        print(f"Brain: Gerando relatório PDF em {caminho_arquivo}...")
        
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib import colors
        except ImportError:
            print(" >> Erro: Biblioteca 'reportlab' não instalada. Execute 'pip install reportlab'.")
            return

        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        doc = SimpleDocTemplate(caminho_arquivo, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        elements.append(Paragraph("Relatório Estatístico Mega-Sena", styles['Title']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Base de dados: {len(todos)} concursos analisados.", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # 1. Frequência (Quentes)
        elements.append(Paragraph("1. Números Mais Frequentes (Quentes)", styles['Heading2']))
        frequencia = {i: 0 for i in range(1, 61)}
        for sorteio in todos:
            for num in sorteio[1:]:
                frequencia[num] += 1
        top_quentes = sorted(frequencia.items(), key=lambda x: x[1], reverse=True)[:10]
        data_quentes = [["Dezena", "Frequência"]] + [[str(n), str(q)] for n, q in top_quentes]
        
        t_quentes = Table(data_quentes, colWidths=[100, 100])
        t_quentes.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t_quentes)
        elements.append(Spacer(1, 12))

        # 2. Atrasos (Frias)
        elements.append(Paragraph("2. Números Mais Atrasados (Frias)", styles['Heading2']))
        concurso_atual = todos[0][0]
        atrasos = {}
        encontrados = set()
        for sorteio in todos:
            concurso = sorteio[0]
            for num in sorteio[1:]:
                if num not in encontrados:
                    atrasos[num] = concurso_atual - concurso
                    encontrados.add(num)
            if len(encontrados) == 60: break
        top_frias = sorted(atrasos.items(), key=lambda x: x[1], reverse=True)[:10]
        data_frias = [["Dezena", "Atraso (Concursos)"]] + [[str(n), str(q)] for n, q in top_frias]
        
        t_frias = Table(data_frias, colWidths=[100, 150])
        t_frias.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t_frias)
        elements.append(Spacer(1, 12))

        # 3. Par/Ímpar
        elements.append(Paragraph("3. Distribuição Par/Ímpar", styles['Heading2']))
        padroes = {"0P-6I": 0, "1P-5I": 0, "2P-4I": 0, "3P-3I": 0, "4P-2I": 0, "5P-1I": 0, "6P-0I": 0}
        total_sorteios = len(todos)
        for sorteio in todos:
            dezenas = sorteio[1:]
            pares = sum(1 for num in dezenas if num % 2 == 0)
            impares = 6 - pares
            padroes[f"{pares}P-{impares}I"] += 1
        data_pi = [["Padrão", "Qtd", "%"]] + [[p, str(q), f"{(q/total_sorteios)*100:.2f}%"] for p, q in sorted(padroes.items(), key=lambda x: x[1], reverse=True)]
        
        t_pi = Table(data_pi, colWidths=[100, 80, 80])
        t_pi.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('GRID', (0, 0), (-1, -1), 1, colors.black)]))
        elements.append(t_pi)

        # 4. Temperatura (Gráfico)
        elements.append(Paragraph("4. Temperatura dos Sorteios (Soma das Dezenas)", styles['Heading2']))
        elements.append(Paragraph("Gráfico de linha mostrando a variação da soma das dezenas ao longo dos últimos 50 concursos.", styles['Normal']))
        elements.append(Spacer(1, 12))

        # Dados para o gráfico (Últimos 50, ordem cronológica)
        recentes = todos[:50][::-1]
        concursos = [s[0] for s in recentes]
        somas = [sum(s[1:]) for s in recentes]
        media_geral = sum([sum(s[1:]) for s in todos]) / len(todos)

        plt.figure(figsize=(8, 4))
        plt.plot(concursos, somas, color='orange', linewidth=2, label='Soma')
        plt.axhline(y=media_geral, color='blue', linestyle='--', label=f'Média ({media_geral:.0f})')
        plt.title('Temperatura dos Últimos 50 Concursos')
        plt.xlabel('Concurso')
        plt.ylabel('Soma')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()

        img = Image(buf, width=450, height=225)
        elements.append(img)

        doc.build(elements)
        print(f" >> Relatório PDF gerado com sucesso: {caminho_arquivo}")

    def analisar_temperatura(self):
        """Analisa a 'Temperatura' (soma das dezenas) dos sorteios."""
        print("Brain: Analisando temperatura (soma) dos sorteios...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        somas = [sum(s[1:]) for s in todos]
        media = sum(somas) / len(somas)
        
        print(f" >> Média da Soma (Temperatura Ideal): {media:.2f}")
        print(f" >> Mínimo Registrado: {min(somas)}")
        print(f" >> Máximo Registrado: {max(somas)}")
        
        # Tendência dos últimos 10
        recentes = somas[:10]
        media_recentes = sum(recentes) / len(recentes)
        
        status = "Neutro"
        if media_recentes > media + 15: status = "Quente (Tendência de alta)"
        elif media_recentes < media - 15: status = "Frio (Tendência de baixa)"
        
        print(f" >> Média dos últimos 10 concursos: {media_recentes:.2f} ({status})")

    def analisar_dezenas_gemeas(self):
        """Analisa a frequência das Dezenas Gêmeas (11, 22, 33, 44, 55)."""
        print("Brain: Analisando Dezenas Gêmeas...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        gemeas = {11, 22, 33, 44, 55}
        contagem_individual = {g: 0 for g in gemeas}
        contagem_por_sorteio = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total_sorteios = len(todos)

        for sorteio in todos:
            dezenas = sorteio[1:]
            qtd_gemeas = sum(1 for num in dezenas if num in gemeas)
            contagem_por_sorteio[qtd_gemeas] += 1
            
            for num in dezenas:
                if num in gemeas:
                    contagem_individual[num] += 1

        print(f" >> Frequência de Dezenas Gêmeas em {total_sorteios} concursos:")
        
        print("    --- Por Quantidade no Sorteio ---")
        for qtd, count in contagem_por_sorteio.items():
            if count > 0:
                porcentagem = (count / total_sorteios) * 100
                print(f"    {qtd} Gêmeas: {count} vezes ({porcentagem:.2f}%)")

        print("    --- Frequência Individual ---")
        ranking = sorted(contagem_individual.items(), key=lambda x: x[1], reverse=True)
        for num, qtd in ranking:
            media = qtd / total_sorteios
            print(f"    Dezena {num}: {qtd} vezes (Média: {media:.2f}/jogo)")

    def analisar_dezenas_invertidas(self):
        """Analisa a frequência de Dezenas Invertidas (ex: 12 e 21) saindo juntas."""
        print("Brain: Analisando Dezenas Invertidas...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Pares invertidos possíveis na Mega-Sena (1-60)
        pares_invertidos = [
            (1, 10), (2, 20), (3, 30), (4, 40), (5, 50), (6, 60),
            (12, 21), (13, 31), (14, 41), (15, 51),
            (23, 32), (24, 42), (25, 52),
            (34, 43), (35, 53),
            (45, 54)
        ]
        
        contagem = {par: 0 for par in pares_invertidos}
        total_sorteios = len(todos)
        sorteios_com_invertidas = 0

        for sorteio in todos:
            dezenas = set(sorteio[1:])
            encontrou_no_sorteio = False
            for p1, p2 in pares_invertidos:
                if p1 in dezenas and p2 in dezenas:
                    contagem[(p1, p2)] += 1
                    encontrou_no_sorteio = True
            
            if encontrou_no_sorteio:
                sorteios_com_invertidas += 1

        print(f" >> Análise de Dezenas Invertidas em {total_sorteios} concursos:")
        porcentagem_total = (sorteios_com_invertidas / total_sorteios) * 100
        print(f"    Sorteios com pelo menos um par invertido: {sorteios_com_invertidas} ({porcentagem_total:.2f}%)")
        
        print("    --- Frequência por Par ---")
        ranking = sorted(contagem.items(), key=lambda x: x[1], reverse=True)
        for (p1, p2), qtd in ranking:
            if qtd > 0:
                media = (qtd / total_sorteios) * 100
                print(f"    Par ({p1:02d}, {p2:02d}): {qtd} vezes ({media:.2f}%)")

    def analisar_pares_viciados(self):
        """Analisa os pares de números que mais saem juntos (Pares Viciados)."""
        print("Brain: Analisando Pares Viciados (mais frequentes)...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        pares_counts = {}
        total_sorteios = len(todos)

        for sorteio in todos:
            dezenas = sorted(sorteio[1:])
            for par in combinations(dezenas, 2):
                pares_counts[par] = pares_counts.get(par, 0) + 1

        ranking = sorted(pares_counts.items(), key=lambda x: x[1], reverse=True)

        print(f" >> Top 20 Pares mais frequentes em {total_sorteios} concursos:")
        for par, qtd in ranking[:20]:
            media = (qtd / total_sorteios) * 100
            print(f"    Par {par}: {qtd} vezes ({media:.4f}%)")

    def analisar_trincas(self):
        """Analisa as trincas (conjuntos de 3 números) mais frequentes."""
        print("Brain: Analisando Trincas mais frequentes...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        trincas_counts = {}
        total_sorteios = len(todos)

        for sorteio in todos:
            dezenas = sorted(sorteio[1:])
            for trinca in combinations(dezenas, 3):
                trincas_counts[trinca] = trincas_counts.get(trinca, 0) + 1

        ranking = sorted(trincas_counts.items(), key=lambda x: x[1], reverse=True)

        print(f" >> Top 20 Trincas mais frequentes em {total_sorteios} concursos:")
        for trinca, qtd in ranking[:20]:
            media = (qtd / total_sorteios) * 100
            print(f"    Trinca {trinca}: {qtd} vezes ({media:.4f}%)")

    def analisar_quadras(self):
        """Analisa as quadras (conjuntos de 4 números) mais frequentes."""
        print("Brain: Analisando Quadras mais frequentes (Isso pode demorar um pouco)...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        quadras_counts = {}
        total_sorteios = len(todos)
        
        # Processamento pode ser lento dependendo do tamanho do histórico
        for sorteio in todos:
            dezenas = sorted(sorteio[1:])
            for quadra in combinations(dezenas, 4):
                quadras_counts[quadra] = quadras_counts.get(quadra, 0) + 1

        ranking = sorted(quadras_counts.items(), key=lambda x: x[1], reverse=True)

        print(f" >> Top 20 Quadras mais frequentes em {total_sorteios} concursos:")
        for quadra, qtd in ranking[:20]:
            media = (qtd / total_sorteios) * 100
            print(f"    Quadra {quadra}: {qtd} vezes ({media:.4f}%)")

    def analisar_quinas(self):
        """Analisa as quinas (conjuntos de 5 números) mais frequentes."""
        print("Brain: Analisando Quinas mais frequentes...")
        print(" >> Nota: Repetições de quinas são eventos extremamente raros.")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        quinas_counts = {}
        total_sorteios = len(todos)
        
        for sorteio in todos:
            dezenas = sorted(sorteio[1:])
            for quina in combinations(dezenas, 5):
                quinas_counts[quina] = quinas_counts.get(quina, 0) + 1

        ranking = sorted(quinas_counts.items(), key=lambda x: x[1], reverse=True)

        print(f" >> Top 20 Quinas mais frequentes em {total_sorteios} concursos:")
        for quina, qtd in ranking[:20]:
            media = (qtd / total_sorteios) * 100
            print(f"    Quina {quina}: {qtd} vezes ({media:.5f}%)")

    def analisar_senas_repetidas(self):
        """Analisa se alguma Sena (6 números) já se repetiu na história."""
        print("Brain: Analisando Senas repetidas...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        senas_counts = {}
        repetidas = []

        for sorteio in todos:
            # Converte lista para tupla para poder usar como chave de dicionário
            sena = tuple(sorted(sorteio[1:]))
            senas_counts[sena] = senas_counts.get(sena, 0) + 1

        print(f" >> Análise de {len(todos)} concursos realizada.")
        repetidas = [s for s, qtd in senas_counts.items() if qtd > 1]
        
        if not repetidas:
            print(" >> Nenhuma Sena repetida encontrada em toda a história.")
        else:
            print(f" >> ALERTA: Encontradas {len(repetidas)} Senas repetidas!")
            for sena in repetidas:
                print(f"    Sena {sena}: Saiu {senas_counts[sena]} vezes.")

    def analisar_dezenas_vizinhas(self):
        """Analisa a frequência de pares de números consecutivos (vizinhos)."""
        print("Brain: Analisando Dezenas Vizinhas (consecutivas)...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        vizinhos_counts = {}
        total_sorteios = len(todos)
        sorteios_com_vizinhos = 0

        for sorteio in todos:
            dezenas = sorted(sorteio[1:])
            tem_vizinho = False
            for i in range(len(dezenas) - 1):
                if dezenas[i+1] == dezenas[i] + 1:
                    par = (dezenas[i], dezenas[i+1])
                    vizinhos_counts[par] = vizinhos_counts.get(par, 0) + 1
                    tem_vizinho = True
            
            if tem_vizinho:
                sorteios_com_vizinhos += 1

        print(f" >> Análise de Dezenas Vizinhas em {total_sorteios} concursos:")
        porcentagem_total = (sorteios_com_vizinhos / total_sorteios) * 100
        print(f"    Sorteios com pelo menos um par vizinho: {sorteios_com_vizinhos} ({porcentagem_total:.2f}%)")
        
        print("    --- Top 20 Pares Vizinhos Mais Frequentes ---")
        ranking = sorted(vizinhos_counts.items(), key=lambda x: x[1], reverse=True)
        
        for par, qtd in ranking[:20]:
            media = (qtd / total_sorteios) * 100
            print(f"    Par {par}: {qtd} vezes ({media:.2f}%)")

    def analisar_intervalos(self):
        """Analisa os intervalos (gaps) entre as dezenas sorteadas."""
        print("Brain: Analisando intervalos (gaps) entre dezenas...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        total_gaps = []
        
        for sorteio in todos:
            dezenas = sorted(sorteio[1:])
            # Calcula a diferença entre o número atual e o próximo
            gaps = [dezenas[i+1] - dezenas[i] for i in range(len(dezenas)-1)]
            total_gaps.extend(gaps)

        if not total_gaps:
            print(" >> Nenhum intervalo calculado.")
            return

        media_geral = sum(total_gaps) / len(total_gaps)
        min_gap = min(total_gaps)
        max_gap = max(total_gaps)
        
        # Frequência dos tamanhos de gap
        freq_gaps = {}
        for g in total_gaps:
            freq_gaps[g] = freq_gaps.get(g, 0) + 1
            
        top_gaps = sorted(freq_gaps.items(), key=lambda x: x[1], reverse=True)[:5]

        print(f" >> Análise de Intervalos em {len(todos)} concursos:")
        print(f"    Média Geral de distância entre dezenas: {media_geral:.2f}")
        print(f"    Menor intervalo: {min_gap} (Números consecutivos)")
        print(f"    Maior intervalo entre duas dezenas: {max_gap}")
        print("    --- Intervalos mais comuns ---")
        for gap, qtd in top_gaps:
            porc = (qtd / len(total_gaps)) * 100
            print(f"    Diferença de {gap}: {qtd} vezes ({porc:.2f}%)")

    def analisar_primos_gemeos(self):
        """Analisa a frequência de Números Primos Gêmeos (ex: 3 e 5) saindo juntos."""
        print("Brain: Analisando Primos Gêmeos...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Primos Gêmeos no intervalo 1-60
        # (3, 5), (5, 7), (11, 13), (17, 19), (29, 31), (41, 43)
        primos_gemeos = [
            (3, 5), (5, 7), (11, 13), (17, 19), (29, 31), (41, 43)
        ]
        
        contagem = {par: 0 for par in primos_gemeos}
        total_sorteios = len(todos)
        sorteios_com_gemeos = 0

        for sorteio in todos:
            dezenas = set(sorteio[1:])
            encontrou_no_sorteio = False
            for p1, p2 in primos_gemeos:
                if p1 in dezenas and p2 in dezenas:
                    contagem[(p1, p2)] += 1
                    encontrou_no_sorteio = True
            
            if encontrou_no_sorteio:
                sorteios_com_gemeos += 1

        print(f" >> Análise de Primos Gêmeos em {total_sorteios} concursos:")
        porcentagem_total = (sorteios_com_gemeos / total_sorteios) * 100
        print(f"    Sorteios com pelo menos um par de primos gêmeos: {sorteios_com_gemeos} ({porcentagem_total:.2f}%)")
        
        print("    --- Frequência por Par ---")
        ranking = sorted(contagem.items(), key=lambda x: x[1], reverse=True)
        for (p1, p2), qtd in ranking:
            if qtd > 0:
                media = (qtd / total_sorteios) * 100
                print(f"    Par ({p1:02d}, {p2:02d}): {qtd} vezes ({media:.2f}%)")

    def analisar_fibonacci(self):
        """Analisa a frequência de números da sequência de Fibonacci."""
        print("Brain: Analisando números de Fibonacci...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Fibonacci na Mega-Sena (1-60)
        fibonacci = {1, 2, 3, 5, 8, 13, 21, 34, 55}
        contagem_individual = {n: 0 for n in fibonacci}
        contagem_por_sorteio = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        total_sorteios = len(todos)

        for sorteio in todos:
            dezenas = sorteio[1:]
            qtd_fib = sum(1 for num in dezenas if num in fibonacci)
            contagem_por_sorteio[qtd_fib] += 1
            
            for num in dezenas:
                if num in fibonacci:
                    contagem_individual[num] += 1

        print(f" >> Frequência de Fibonacci em {total_sorteios} concursos:")
        
        print("    --- Por Quantidade no Sorteio ---")
        for qtd, count in contagem_por_sorteio.items():
            if count > 0:
                porcentagem = (count / total_sorteios) * 100
                print(f"    {qtd} Fibonacci: {count} vezes ({porcentagem:.2f}%)")

        print("    --- Frequência Individual ---")
        ranking = sorted(contagem_individual.items(), key=lambda x: x[1], reverse=True)
        for num, qtd in ranking:
            media = (qtd / total_sorteios) * 100
            print(f"    Fibonacci {num}: {qtd} vezes ({media:.2f}%)")

    def analisar_multiplos_de_3(self):
        """Analisa a frequência de números múltiplos de 3."""
        print("Brain: Analisando números múltiplos de 3...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Múltiplos de 3 na Mega-Sena (1-60)
        multiplos = set(range(3, 61, 3))
        contagem_individual = {n: 0 for n in multiplos}
        contagem_por_sorteio = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        total_sorteios = len(todos)

        for sorteio in todos:
            dezenas = sorteio[1:]
            qtd_multiplos = sum(1 for num in dezenas if num in multiplos)
            contagem_por_sorteio[qtd_multiplos] += 1
            
            for num in dezenas:
                if num in multiplos:
                    contagem_individual[num] += 1

        print(f" >> Frequência de Múltiplos de 3 em {total_sorteios} concursos:")
        
        print("    --- Por Quantidade no Sorteio ---")
        for qtd, count in contagem_por_sorteio.items():
            if count > 0:
                porcentagem = (count / total_sorteios) * 100
                print(f"    {qtd} Múltiplos: {count} vezes ({porcentagem:.2f}%)")

        print("    --- Frequência Individual ---")
        ranking = sorted(contagem_individual.items(), key=lambda x: x[1], reverse=True)
        for num, qtd in ranking:
            media = (qtd / total_sorteios) * 100
            print(f"    Número {num}: {qtd} vezes ({media:.2f}%)")

    def salvar_sugestao_arquivo(self, texto):
        """Salva a sugestão gerada em um arquivo de texto."""
        arquivo = os.path.join(os.path.dirname(__file__), 'meus_jogos.txt')
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(arquivo, 'a', encoding='utf-8') as f:
                f.write(f"\n--- Sugestão gerada em {timestamp} ---\n")
                f.write(texto)
                f.write("\n" + "-"*40 + "\n")
            print(f" >> Sugestão salva automaticamente em: {arquivo}")
        except Exception as e:
            print(f" >> Erro ao salvar sugestão em arquivo: {e}")

    def abrir_meus_jogos(self):
        """Abre o arquivo de sugestões salvas no editor padrão."""
        arquivo = os.path.join(os.path.dirname(__file__), 'meus_jogos.txt')
        if not os.path.exists(arquivo):
            print(" >> Arquivo 'meus_jogos.txt' não encontrado. Criando arquivo vazio...")
            try:
                with open(arquivo, 'w', encoding='utf-8') as f:
                    f.write("--- Histórico de Palpites ---\n")
            except Exception as e:
                print(f" >> Erro ao criar arquivo: {e}")
                return
        
        try:
            os.startfile(arquivo)
        except Exception as e:
            print(f" >> Erro ao abrir arquivo: {e}")

    def verificar_integridade_banco(self):
        """Verifica a integridade do banco de dados e corrige estrutura."""
        print("Brain: Verificando integridade do banco de dados...")
        sucesso, mensagem = self.db_manager.verificar_integridade()
        if sucesso:
            print(f" >> Sucesso: {mensagem}")
        else:
            print(f" >> ERRO: {mensagem}")
            print(" >> Recomendação: Tente restaurar um backup.")

    def abrir_arquivo_excel(self):
        """Abre o arquivo mega_sena.xlsx no editor padrão."""
        arquivo = os.path.join(os.path.dirname(__file__), 'mega_sena.xlsx')
        if not os.path.exists(arquivo):
            print(" >> Arquivo 'mega_sena.xlsx' não encontrado na pasta do projeto.")
            return
        
        try:
            os.startfile(arquivo)
        except Exception as e:
            print(f" >> Erro ao abrir arquivo Excel: {e}")

    def analisar_numeros_espelho(self):
        """Analisa a frequência individual de números espelho (ex: 13 e 31)."""
        print("Brain: Analisando Números Espelho...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Lista de pares espelho (inversos)
        pares = [
            (1, 10), (2, 20), (3, 30), (4, 40), (5, 50), (6, 60),
            (12, 21), (13, 31), (14, 41), (15, 51),
            (23, 32), (24, 42), (25, 52),
            (34, 43), (35, 53),
            (45, 54)
        ]
        
        # Coletar todos os números que são espelho
        numeros_espelho = set()
        for p1, p2 in pares:
            numeros_espelho.add(p1)
            numeros_espelho.add(p2)
            
        contagem = {n: 0 for n in numeros_espelho}
        
        for sorteio in todos:
            for num in sorteio[1:]:
                if num in numeros_espelho:
                    contagem[num] += 1
                    
        print(f" >> Comparativo de Frequência entre Espelhos ({len(todos)} concursos):")
        for p1, p2 in pares:
            qtd1 = contagem[p1]
            qtd2 = contagem[p2]
            diff = abs(qtd1 - qtd2)
            lider = p1 if qtd1 > qtd2 else p2
            print(f"    {p1:02d} ({qtd1}x) vs {p2:02d} ({qtd2}x) | Diferença: {diff} (Líder: {lider})")
        print("    --- Frequência por Par ---")
        ranking = sorted(contagem.items(), key=lambda x: x[1], reverse=True)
        for (p1, p2), qtd in ranking:
            if qtd > 0:
                media = (qtd / total_sorteios) * 100
                print(f"    Par ({p1:02d}, {p2:02d}): {qtd} vezes ({media:.2f}%)")

    def analisar_fibonacci(self):
        """Analisa a frequência de números da sequência de Fibonacci."""
        print("Brain: Analisando números de Fibonacci...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Fibonacci na Mega-Sena (1-60)
        fibonacci = {1, 2, 3, 5, 8, 13, 21, 34, 55}
        contagem_individual = {n: 0 for n in fibonacci}
        contagem_por_sorteio = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        total_sorteios = len(todos)

        for sorteio in todos:
            dezenas = sorteio[1:]
            qtd_fib = sum(1 for num in dezenas if num in fibonacci)
            contagem_por_sorteio[qtd_fib] += 1
            
            for num in dezenas:
                if num in fibonacci:
                    contagem_individual[num] += 1

        print(f" >> Frequência de Fibonacci em {total_sorteios} concursos:")
        
        print("    --- Por Quantidade no Sorteio ---")
        for qtd, count in contagem_por_sorteio.items():
            if count > 0:
                porcentagem = (count / total_sorteios) * 100
                print(f"    {qtd} Fibonacci: {count} vezes ({porcentagem:.2f}%)")

        print("    --- Frequência Individual ---")
        ranking = sorted(contagem_individual.items(), key=lambda x: x[1], reverse=True)
        for num, qtd in ranking:
            media = (qtd / total_sorteios) * 100
            print(f"    Fibonacci {num}: {qtd} vezes ({media:.2f}%)")

    def analisar_multiplos_de_3(self):
        """Analisa a frequência de números múltiplos de 3."""
        print("Brain: Analisando números múltiplos de 3...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Múltiplos de 3 na Mega-Sena (1-60)
        multiplos = set(range(3, 61, 3))
        contagem_individual = {n: 0 for n in multiplos}
        contagem_por_sorteio = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        total_sorteios = len(todos)

        for sorteio in todos:
            dezenas = sorteio[1:]
            qtd_multiplos = sum(1 for num in dezenas if num in multiplos)
            contagem_por_sorteio[qtd_multiplos] += 1
            
            for num in dezenas:
                if num in multiplos:
                    contagem_individual[num] += 1

        print(f" >> Frequência de Múltiplos de 3 em {total_sorteios} concursos:")
        
        print("    --- Por Quantidade no Sorteio ---")
        for qtd, count in contagem_por_sorteio.items():
            if count > 0:
                porcentagem = (count / total_sorteios) * 100
                print(f"    {qtd} Múltiplos: {count} vezes ({porcentagem:.2f}%)")

        print("    --- Frequência Individual ---")
        ranking = sorted(contagem_individual.items(), key=lambda x: x[1], reverse=True)
        for num, qtd in ranking:
            media = (qtd / total_sorteios) * 100
            print(f"    Número {num}: {qtd} vezes ({media:.2f}%)")
            dezenas = sorteio[1:]
            qtd_multiplos = sum(1 for num in dezenas if num in multiplos)
            contagem_por_sorteio[qtd_multiplos] += 1
            
            for num in dezenas:
                if num in multiplos:
                    contagem_individual[num] += 1

        print(f" >> Frequência de Múltiplos de 3 em {total_sorteios} concursos:")
        
        print("    --- Por Quantidade no Sorteio ---")
        for qtd, count in contagem_por_sorteio.items():
            if count > 0:
                porcentagem = (count / total_sorteios) * 100
                print(f"    {qtd} Múltiplos: {count} vezes ({porcentagem:.2f}%)")

        print("    --- Frequência Individual ---")
        ranking = sorted(contagem_individual.items(), key=lambda x: x[1], reverse=True)
        for num, qtd in ranking:
            media = (qtd / total_sorteios) * 100
            print(f"    Número {num}: {qtd} vezes ({media:.2f}%)")
        # Fibonacci na Mega-Sena (1-60)
        fibonacci = {1, 2, 3, 5, 8, 13, 21, 34, 55}
        contagem_individual = {n: 0 for n in fibonacci}
        contagem_por_sorteio = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        total_sorteios = len(todos)

        for sorteio in todos:
            dezenas = sorteio[1:]
            qtd_fib = sum(1 for num in dezenas if num in fibonacci)
            contagem_por_sorteio[qtd_fib] += 1
            
            for num in dezenas:
                if num in fibonacci:
                    contagem_individual[num] += 1

        print(f" >> Frequência de Fibonacci em {total_sorteios} concursos:")
        
        print("    --- Por Quantidade no Sorteio ---")
        for qtd, count in contagem_por_sorteio.items():
            if count > 0:
                porcentagem = (count / total_sorteios) * 100
                print(f"    {qtd} Fibonacci: {count} vezes ({porcentagem:.2f}%)")

        print("    --- Frequência Individual ---")
        ranking = sorted(contagem_individual.items(), key=lambda x: x[1], reverse=True)
        for num, qtd in ranking:
            media = (qtd / total_sorteios) * 100
            print(f"    Fibonacci {num}: {qtd} vezes ({media:.2f}%)")

    def analisar_multiplos_de_3(self):
        """Analisa a frequência de números múltiplos de 3."""
        print("Brain: Analisando números múltiplos de 3...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Base de dados vazia.")
            return

        # Múltiplos de 3 na Mega-Sena (1-60)
        multiplos = set(range(3, 61, 3))
        contagem_individual = {n: 0 for n in multiplos}
        contagem_por_sorteio = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        total_sorteios = len(todos)

        for sorteio in todos:
            dezenas = sorteio[1:]
            qtd_multiplos = sum(1 for num in dezenas if num in multiplos)
            contagem_por_sorteio[qtd_multiplos] += 1
            
            for num in dezenas:
                if num in multiplos:
                    contagem_individual[num] += 1

        print(f" >> Frequência de Múltiplos de 3 em {total_sorteios} concursos:")
        
        print("    --- Por Quantidade no Sorteio ---")
        for qtd, count in contagem_por_sorteio.items():
            if count > 0:
                porcentagem = (count / total_sorteios) * 100
                print(f"    {qtd} Múltiplos: {count} vezes ({porcentagem:.2f}%)")

        print("    --- Frequência Individual ---")
        ranking = sorted(contagem_individual.items(), key=lambda x: x[1], reverse=True)
        for num, qtd in ranking:
            media = (qtd / total_sorteios) * 100
            print(f"    Número {num}: {qtd} vezes ({media:.2f}%)")
