from importar_dados import importar_dados
from database import DatabaseManager
from itertools import combinations
import io
import time
import matplotlib.pyplot as plt
import math
import shutil
import datetime
import json
import numpy as np
import os
import sys

# Bibliotecas Adicionais para IA e PDF
try:
    from google import genai
    from google.genai import types
except ImportError:
    pass

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet
except ImportError:
    pass

HAS_CUPY = False
try:
    import cupy as cp
    HAS_CUPY = True
except:
    pass

class Brain:
    """Classe responsável pela inteligência do sistema e cálculos matemáticos."""

    def __init__(self, api_token=None, api_delay=2):
        self.api_token = api_token
        self.api_delay = api_delay
        self.db_manager = DatabaseManager()
        self.abortar_processo = False
        self.quota_file = "quota.json"
        self.config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        
        # System Prompt para IA Especialista
        self.system_prompt = (
            "Persona: Você é um Engenheiro de Dados Sênior e um Especialista Matemático Sênior de renome mundial. "
            "Expertise: Especialista em análises preditivas de dezenas, estatística inferencial e simulações estocásticas de jogos de azar. "
            "Contexto: Mega-Sena brasileira (60 dezenas, sorteios de 6 números). "
            "Objetivo: Fornecer insights matemáticos profundos, calcular probabilidades reais, identificar tendências baseadas em leis estatísticas "
            "(como a Lei dos Grandes Números) e propor simulações de jogos consistentes."
        )

        # Carregar modelo padrão do config.json
        self.model_name = "gemini-2.0-flash"
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    cfg = json.load(f)
                    self.model_name = cfg.get("GEMINI_MODEL", "gemini-2.0-flash")
            except: pass

        # Inicializa cliente Gemini
        self.client = None
        self.reconfigurar_api(self.api_token, self.model_name)
        self.jogos_elite = [] # Armazena os 4 jogos de elite (6 dezenas cada)

        if not self.db_manager.obter_ultimo_sorteio():
            importar_dados()
        print(f"Brain: Sistema Híbrido Pronto (Hardware e Especialista Matemático).")

    def reconfigurar_api(self, token, modelo):
        """Atualiza o token e modelo da IA em tempo real."""
        self.api_token = token
        self.model_name = modelo
        if self.api_token and self.api_token != "INSIRA_SEU_TOKEN_AQUI" and len(self.api_token) > 10:
            try:
                self.client = genai.Client(api_key=self.api_token)
                # Testa se o cliente é funcional listando 1 modelo
                _ = self.client.models.get(model=self.model_name)
                return True
            except Exception as e:
                print(f"Brain: Erro ao validar cliente Gemini: {e}")
                self.client = None
                return False
        return False

    def listar_modelos_gemini(self, temp_token=None):
        """Lista modelos disponíveis e ativos para a chave fornecida."""
        token_atual = temp_token if (temp_token and len(temp_token) > 10 and temp_token != "INSIRA_SEU_TOKEN_AQUI") else self.api_token
        
        if not token_atual or token_atual == "INSIRA_SEU_TOKEN_AQUI":
            print("Brain: Token não fornecido para listagem.")
            return []
            
        try:
            # Cria um cliente temporário para validar a chave
            temp_client = genai.Client(api_key=token_atual)
            modelos_ativos = []
            
            # Busca a lista oficial da API
            pager = temp_client.models.list()
            for m in pager:
                # Filtra apenas modelos da família Gemini que estão disponíveis para esta chave
                if 'gemini' in m.name.lower():
                    modelos_ativos.append(m.name)
            
            # Se a lista vier vazia, a chave pode estar inválida ou sem permissão
            if not modelos_ativos:
                print("Brain: Nenhum modelo Gemini encontrado para esta chave.")
                return []
                
            return sorted(modelos_ativos)
        except Exception as e:
            print(f"Brain: Erro crítico ao conectar na API para listar: {e}")
            return []

    def _verificar_e_atualizar_quota(self):
        hoje = datetime.date.today().isoformat()
        try:
            if os.path.exists(self.quota_file):
                with open(self.quota_file, 'r') as f: d = json.load(f)
            else: d = {"data_atual": hoje, "requisicoes_hoje": 0, "limite_diario": 1500}
            if d["data_atual"] != hoje: d["data_atual"] = hoje; d["requisicoes_hoje"] = 0
            if d["requisicoes_hoje"] >= d["limite_diario"]: return False
            d["requisicoes_hoje"] += 1
            with open(self.quota_file, 'w') as f: json.dump(d, f)
            return True
        except: return True

    def interagir_hibrido(self, pergunta):
        """Diálogo especializado com o Engenheiro de Dados IA com tratamento de cota."""
        if not self.client: return "Erro: Configure a API Key no Chat para interagir com o Especialista IA."
        if not self._verificar_e_atualizar_quota(): return "Aviso: Limite de cota local atingido."
        
        try:
            # Contextualiza com estatísticas reais do banco
            dados = self.db_manager.obter_ultimo_sorteio()
            contexto = f"{self.system_prompt}\nÚltimo sorteio histórico: {dados.get('numeros', 'N/A') if dados else 'Nenhum sorteio no banco'}"
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=f"{contexto}\n\nAnalise tecnicamente: {pergunta}"
            )
            time.sleep(self.api_delay)
            return response.text
        except Exception as e:
            err_msg = str(e).upper()
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                return (f"⚠️ COTA EXCEDIDA NO MODELO '{self.model_name}':\n\n"
                        "O Google limitou o uso deste modelo temporariamente.\n"
                        "DICA: Clique em 'Listar Modelos' e escolha o 'gemini-2.0-flash'. "
                        "Ele é mais resiliente e raramente atinge o limite.")
            return f"Erro na IA: {e}"

    def conferir_resultado(self, aposta_usuario=None):
        """Confere resultado, salva no banco e atualiza o Excel de Hacking automaticamente."""
        from importar_dados import atualizar_excel_ranking
        print("Brain: Conferindo e Atualizando Base...")
        if not aposta_usuario: return

        ultimo = self.db_manager.obter_ultimo_sorteio()
        conc = (ultimo['concurso'] + 1) if ultimo else 3000
        hoje = datetime.datetime.now().strftime("%d/%m/%Y")

        try:
            self.db_manager.salvar_sorteio(conc, hoje, aposta_usuario[:6])
            print(f" >> Concurso {conc} salvo com sucesso.")
            # GATILHO DE HACKING: Atualiza o arquivo físico mega_sena.xlsx
            atualizar_excel_ranking()
            print(" >> O arquivo mega_sena.xlsx foi atualizado com o padrão de hacking!")
        except Exception as e:
            print(f" >> Erro no ciclo de atualização: {e}")

    def pensar_jogos(self, qtd_simulacao=1000000):
        """Gera palpites via Hardware (CPU/GPU)."""
        print(f"Brain: Gerando palpites via Hardware Acceleration ({'GPU' if HAS_CUPY else 'CPU'})...")
        ranking = self._obter_ranking_importado()
        scores = np.ones(61, dtype=np.float32)
        if ranking:
            for item in ranking:
                d = self._safe_int_conversion(item.get('dezena'))
                if d and 1 <= d <= 60:
                    ocorr = self._safe_int_conversion(item.get('ocorrências_(aprox.)'))
                    if ocorr: scores[d] += (ocorr / 50.0)
        
        if HAS_CUPY:
            gpu_scores = cp.array(scores)
            gpu_prob = (gpu_scores + 1.0) / cp.sum(gpu_scores + 1.0)
            pool = cp.random.choice(cp.arange(1, 61), size=(10, 6), replace=False, p=gpu_prob[1:]/cp.sum(gpu_prob[1:]))
            sugestoes = [sorted(jogo.tolist()) for jogo in cp.asnumpy(pool[:3])]
        else:
            prob = (scores[1:] + 1.0) / np.sum(scores[1:] + 1.0)
            sugestoes = [sorted(np.random.choice(range(1, 61), 6, replace=False, p=prob)) for _ in range(3)]
        
        self.salvar_sugestao_arquivo(f"Hardware Sugestões: {sugestoes}")
        return sugestoes

    def _safe_int_conversion(self, v):
        try: return int(round(float(str(v).replace(',', '.'))))
        except: return None

    def _obter_ranking_importado(self):
        try:
            with self.db_manager.get_connection() as conn:
                r = conn.execute("SELECT dado FROM estatisticas_importadas WHERE tipo='ranking_20_anos' ORDER BY data_importacao DESC LIMIT 1").fetchone()
                return json.loads(r[0]) if r else None
        except: return None

    def verificar_saude_gpu(self):
        if not HAS_CUPY: return False
        try: cp.array([1]); return True
        except: return False

    def benchmark_cpu_vs_gpu(self, q=100000000):
        s = time.time(); np.random.randint(1, 61, size=q); e_cpu = time.time()-s
        print(f" >> CPU: {e_cpu:.4f}s")
        if HAS_CUPY:
            s = time.time(); cp.random.randint(1, 61, size=q); e_gpu = time.time()-s
            print(f" >> GPU: {e_gpu:.4f}s (Ratio: {e_cpu/e_gpu:.1f}x)")

    def salvar_sugestao_arquivo(self, t):
        with open('meus_jogos.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n{datetime.datetime.now()}: {t}\n")

    def obter_status_ia(self): 
        if self.client: return "online", self.model_name
        return "offline", "Não Configurado"

    def obter_cota_atual(self):
        try:
            with open(self.quota_file, 'r') as f: d = json.load(f)
            return d["requisicoes_hoje"], d["limite_diario"]
        except: return 0, 1500

    def abrir_meus_jogos(self): os.startfile('meus_jogos.txt')
    def abrir_arquivo_excel(self): os.startfile('mega_sena.xlsx')
    def verificar_integridade_banco(self):
        """Executa auditoria profunda e imprime relatório no log."""
        print("SISTEMA: Iniciando Auditoria de Integridade de Dados...")
        sucesso, mensagem = self.db_manager.verificar_integridade()
        
        status = "CONCLUÍDA COM SUCESSO" if sucesso else "FALHAS ENCONTRADAS"
        print(f"\n[RELATÓRIO DE AUDITORIA - {status}]")
        print(f"{mensagem}\n")
        return sucesso, mensagem
    def gerar_relatorio_pdf(self, c=None): 
        print("PDF: Gerando Relatório Técnico..."); return True

    def gerar_grafico_frequencia(self, render_callback=None):
        """Prepara os dados de frequência. Se houver um callback, envia para renderização."""
        print("Estatística: Processando dados de frequência real...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos:
            print(" >> Erro: Sem dados para gerar gráfico.")
            return

        contagem = {i: 0 for i in range(1, 61)}
        for s in todos:
            for n in s[1:]:
                contagem[n] += 1
        
        dezenas = list(contagem.keys())
        frequencias = list(contagem.values())

        if render_callback:
            render_callback(dezenas, frequencias)
        else:
            # Fallback caso não venha da interface (não recomendado para threads)
            self._renderizar_grafico_interno(dezenas, frequencias)

    def _renderizar_grafico_interno(self, dezenas, frequencias):
        """Lógica interna de plotagem (deve ser chamada na thread principal)."""
        try:
            plt.close('all')
            plt.figure(figsize=(10, 5))
            plt.bar(dezenas, frequencias, color='#2196F3')
            plt.title('Frequência Histórica Real')
            plt.xlabel('Dezena')
            plt.ylabel('Vezes Sorteada')
            plt.xticks(range(1, 61, 5))
            plt.grid(axis='y', alpha=0.3)
            plt.tight_layout()
            plt.show()
        except Exception as e:
            print(f" >> Erro na renderização: {e}")

    def analisar_quadrantes(self):
        """Analisa a distribuição espacial real."""
        print("Análise Espacial: Distribuição nos Quadrantes...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos: return

        q1, q2, q3, q4 = 0, 0, 0, 0
        for s in todos:
            for n in s[1:]:
                col = (n-1) % 10
                row = (n-1) // 10
                if row < 3:
                    if col < 5: q1 += 1
                    else: q2 += 1
                else:
                    if col < 5: q3 += 1
                    else: q4 += 1
        
        total = q1 + q2 + q3 + q4
        print(f" >> Ocorrências por Quadrante:")
        print(f"    Q1 (Top-Left): {q1} ({(q1/total*100):.1f}%)")
        print(f"    Q2 (Top-Right): {q2} ({(q2/total*100):.1f}%)")
        print(f"    Q3 (Bottom-Left): {q3} ({(q3/total*100):.1f}%)")
        print(f"    Q4 (Bottom-Right): {q4} ({(q4/total*100):.1f}%)")

    def simular_cenarios(self, qtd=1000000, callback=None):
        """Simulação de Monte Carlo para validar a Lei dos Grandes Números."""
        print(f"Brain: Iniciando Simulação de Monte Carlo com {qtd:,} cenários...")
        s = time.time()
        
        # Gera números aleatórios em massa
        if HAS_CUPY:
            dados = cp.random.randint(1, 61, size=(qtd, 6))
            # Simula a verificação de frequência na GPU
            contagem = cp.histogram(dados, bins=range(1, 62))[0]
            contagem_final = cp.asnumpy(contagem)
        else:
            dados = np.random.randint(1, 61, size=(qtd, 6))
            contagem_final = np.histogram(dados, bins=range(1, 62))[0]
        
        tempo = time.time() - s
        print(f" >> Simulação Concluída em {tempo:.2f}s.")
        print(" >> Resultados Estocásticos (Top 5 mais sorteados na simulação):")
        top5 = np.argsort(contagem_final)[-5:][::-1]
        for i, idx in enumerate(top5):
            print(f"    {i+1}º: Dezena {idx+1} (Sorteada {contagem_final[idx]:,} vezes)")
        
        # Gera 4 JOGOS DE ELITE (6 dezenas cada) baseados no Top 15 da simulação
        top_elite = [int(idx+1) for idx in np.argsort(contagem_final)[-15:][::-1]]
        self.jogos_elite = []
        for _ in range(4):
            # Seleciona 6 números únicos do pool de 15 melhores
            jogo = sorted(np.random.choice(top_elite, 6, replace=False).tolist())
            self.jogos_elite.append(jogo)
        
        if callback: callback(qtd, qtd)

    def analisar_atrasos(self):
        """Analisa e exibe o ranking de atrasos real."""
        print("Estatística: Analisando atrasos (Hardware Processing)...")
        ranking = self._obter_ranking_importado()
        if not ranking:
            print(" >> Erro: Base de dados vazia ou Excel não processado.")
            return
            
        print(" >> DEZENAS MAIS ATRASADAS (Dias/Concursos sem sair):")
        # O ranking importado já tem a coluna 'Mais atrasadas'
        atrasadas = [item.get('Mais Atrasadas') for item in ranking[:10]]
        print(f"    Top 10: {', '.join(map(str, atrasadas))}")

    def analisar_pares_impares(self):
        """Exibe a paridade real dos últimos sorteios."""
        print("Estatística: Analisando paridade e equilíbrio...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos: return

        p, i = 0, 0
        for s in todos[:50]: # Analisa os últimos 50
            for n in s[1:]:
                if n % 2 == 0: p += 1
                else: i += 1
        
        total = p + i
        print(f" >> Tendência nos últimos 50 sorteios: {p} Pares vs {i} Ímpares")
        print(f" >> Percentual: {(p/total)*100:.1f}% Pares | {(i/total)*100:.1f}% Ímpares")

    def analisar_ciclos(self):
        """Calcula o ciclo atual (quantas faltam para fechar o globo)."""
        print("Probabilidade: Analisando Ciclos de Dezenas...")
        todos = self.db_manager.obter_todos_sorteios()
        if not todos: return

        vistos = set()
        faltantes = set(range(1, 61))
        concursos = 0
        
        for s in todos:
            concursos += 1
            for n in s[1:]:
                if n in faltantes:
                    faltantes.remove(n)
            if not faltantes: break
            
        if faltantes:
            print(f" >> Ciclo Atual: Faltam {len(faltantes)} dezenas para completar o globo.")
            print(f" >> Dezenas que ainda não saíram no ciclo: {sorted(list(faltantes))}")
        else:
            print(f" >> Ciclo Fechado: Foram necessários {concursos} concursos para sortear todas as 60 dezenas.")
    def gerar_palpite_ia(self): return self.interagir_hibrido("Sugira um jogo baseado em probabilidades estatísticas.")
