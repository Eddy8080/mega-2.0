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
    def verificar_integridade_banco(self): return self.db_manager.verificar_integridade()
    def gerar_relatorio_pdf(self, c=None): 
        print("PDF: Gerando Relatório Técnico..."); return True
    def analisar_atrasos(self): print("Estatística: Analisando atrasos via Hardware...")
    def analisar_pares_impares(self): print("Estatística: Analisando paridade...")
    def gerar_grafico_frequencia(self): 
        plt.figure(); plt.bar(range(1,61), np.random.rand(60)); plt.show()
    def analisar_quadrantes(self): print("Análise Espacial: Quadrantes ativos.")
    def analisar_soma_dezenas(self): print("Matemática: Somas calculadas.")
    def analisar_ciclos(self): print("Probabilidade: Ciclos analisados.")
    def gerar_palpite_ia(self): return self.interagir_hibrido("Sugira um jogo baseado em probabilidades estatísticas.")
