import os
import sys
import json
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, filedialog, ttk

class TextRedirector:
    def __init__(self, widget): self.widget = widget
    def write(self, m):
        self.widget.insert("end", m); self.widget.see("end"); self.widget.update_idletasks()
    def flush(self): pass

class Interface:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mega-Sena 2.0: Hardware Acceleration & Expert AI")
        self.root.geometry("1100x850")
        self.brain = None
        self.dark_mode = False
        self._configurar_ui()
        sys.stdout = TextRedirector(self.log_area)

    def _configurar_ui(self):
        # --- FRAME ESQUERDO (MENU) ---
        self.frame_esquerda = tk.Frame(self.root, width=300)
        self.frame_esquerda.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # LEDs de Hardware
        self.frame_status = tk.LabelFrame(self.frame_esquerda, text="Hardware Status")
        self.frame_status.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        self.canvas_cpu = tk.Canvas(self.frame_status, width=20, height=20, highlightthickness=0)
        self.canvas_cpu.pack(side=tk.LEFT, padx=5)
        self.led_cpu = self.canvas_cpu.create_oval(4, 4, 16, 16, fill="gray")
        tk.Label(self.frame_status, text="CPU", font=("Arial", 8)).pack(side=tk.LEFT)

        self.canvas_gpu = tk.Canvas(self.frame_status, width=20, height=20, highlightthickness=0)
        self.canvas_gpu.pack(side=tk.LEFT, padx=(15, 5))
        self.led_gpu = self.canvas_gpu.create_oval(4, 4, 16, 16, fill="gray")
        tk.Label(self.frame_status, text="GPU", font=("Arial", 8)).pack(side=tk.LEFT)

        # Botões de Operação
        self.canvas_scroll = tk.Canvas(self.frame_esquerda, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame_esquerda, command=self.canvas_scroll.yview)
        self.frame_botoes = tk.Frame(self.canvas_scroll)
        self.canvas_scroll.create_window((0,0), window=self.frame_botoes, anchor="nw")
        self.canvas_scroll.configure(yscrollcommand=self.scrollbar.set)
        self.canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.frame_botoes.bind("<Configure>", lambda e: self.canvas_scroll.configure(scrollregion=self.canvas_scroll.bbox("all")))

        def safe(f): return lambda: self._acao_segura(f)

        cats = [
            ("1. Gestão de Dados", [
                ("Importar Jogos Reais", self.importar_padrao),
                ("Abrir mega_sena.xlsx", safe(lambda: self.brain.abrir_arquivo_excel())),
                ("Conferir Resultado", self.solicitar_conferencia),
                ("Integridade do Banco", safe(lambda: self.brain.verificar_integridade_banco())),
            ]),
            ("2. Análises Estatísticas", [
                ("Frequência Real", self.solicitar_grafico_frequencia),
                ("Atrasos e Frios", safe(lambda: self.brain.analisar_atrasos())),
                ("Paridade e Quadrantes", safe(lambda: self.brain.analisar_pares_impares())),
                ("Ciclos de Dezenas", safe(lambda: self.brain.analisar_ciclos())),
                ("Benchmark Hardware", safe(lambda: self.brain.benchmark_cpu_vs_gpu())),
                ("Simulação Monte Carlo", self.solicitar_simulacao),
            ]),
            ("3. Geração Híbrida", [
                ("GERAR PALPITES HÍBRIDOS", safe(lambda: self.brain.pensar_jogos())),
                ("4 JOGOS DE ELITE (Pós-Simulação)", self.mostrar_jogos_elite),
                ("Ver Meus Jogos (.txt)", safe(lambda: self.brain.abrir_meus_jogos())),
            ]),
            ("4. Especialista IA", [
                ("ABRIR CHAT ESPECIALISTA", self.abrir_chat_ia),
                ("Relatório PDF", safe(lambda: self.brain.gerar_relatorio_pdf())),
            ]),
            ("5. Sistema", [
                ("Alternar Tema", self.alternar_tema),
                ("Limpar Logs", self.limpar_tela),
            ])
        ]

        for n, btns in cats:
            lf = tk.LabelFrame(self.frame_botoes, text=n, font=("Arial", 9, "bold"))
            lf.pack(fill=tk.X, padx=5, pady=5)
            for l, c in btns:
                tk.Button(lf, text=l, command=c).pack(fill=tk.X, pady=2, padx=2)

        # --- FRAME DIREITO (LOG) ---
        self.frame_direita = tk.Frame(self.root)
        self.frame_direita.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.log_area = scrolledtext.ScrolledText(self.frame_direita, font=("Consolas", 10), bg="white")
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.progress = ttk.Progressbar(self.frame_direita, orient="horizontal", mode="determinate")
        self.progress.pack(fill=tk.X, pady=5)

    def abrir_chat_ia(self):
        """Abre a janela de chat com layout fixo e funcional."""
        chat_win = tk.Toplevel(self.root)
        chat_win.title("CHAT: Especialista Matemático & Engenheiro de Dados")
        chat_win.geometry("700x850")
        chat_win.minsize(600, 700)
        chat_win.transient(self.root)

        # 1. ÁREA DE CONFIGURAÇÃO (TOP)
        frame_config = tk.LabelFrame(chat_win, text="Configuração da IA", padx=10, pady=10)
        frame_config.pack(fill=tk.X, padx=10, pady=5)

        # Linha 1: API Key e Botão de Listar
        frame_linha1 = tk.Frame(frame_config)
        frame_linha1.pack(fill=tk.X, pady=2)
        tk.Label(frame_linha1, text="API Key:").pack(side=tk.LEFT)
        ent_token = tk.Entry(frame_linha1, show="*", width=40)
        ent_token.insert(0, self.brain.api_token or "")
        ent_token.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        btn_listar = tk.Button(frame_linha1, text="Listar Modelos", command=lambda: self._popula_modelos(lb_mod, ent_token.get()))
        btn_listar.pack(side=tk.RIGHT, padx=5)

        # Linha 2: Modelos e Scroll
        frame_linha2 = tk.Frame(frame_config)
        frame_linha2.pack(fill=tk.X, pady=5)
        tk.Label(frame_linha2, text="Selecione o Modelo Padrão:").pack(anchor="w")
        lb_mod = tk.Listbox(frame_linha2, height=4, exportselection=False)
        lb_mod.pack(side=tk.LEFT, fill=tk.X, expand=True)
        sc_mod = tk.Scrollbar(frame_linha2, command=lb_mod.yview)
        sc_mod.pack(side=tk.RIGHT, fill=tk.Y)
        lb_mod.config(yscrollcommand=sc_mod.set)

        # Carrega a lista automaticamente se já tiver chave
        if self.brain.api_token:
            self._popula_modelos(lb_mod, self.brain.api_token)

        def salvar_modelo():
            t = ent_token.get()
            s = lb_mod.curselection()
            m = lb_mod.get(s[0]) if s else self.brain.model_name
            if self.brain.reconfigurar_api(t, m):
                # Persistir no config.json
                try:
                    with open(self.brain.config_path, 'r') as f: cfg = json.load(f)
                    cfg["GEMINI_API_TOKEN"] = t; cfg["GEMINI_MODEL"] = m
                    with open(self.brain.config_path, 'w') as f: json.dump(cfg, f)
                    messagebox.showinfo("Sucesso", f"Modelo '{m}' ativado e definido como padrão!")
                except: pass
            else: 
                messagebox.showerror("Erro", "Token inválido ou falha de conexão.")

        tk.Button(frame_config, text="SALVAR COMO PADRÃO E ATIVAR", command=salvar_modelo, bg="#c8e6c9", font=("Arial", 9, "bold")).pack(fill=tk.X, pady=5)

        # 2. ÁREA DE MENSAGEM (BOTTOM)
        # É colocado antes da área de texto para que não desapareça ao redimensionar (com pack_propagate)
        frame_input = tk.Frame(chat_win, pady=10)
        frame_input.pack(side=tk.BOTTOM, fill=tk.X, padx=10)

        ent_msg = tk.Entry(frame_input, font=("Arial", 11))
        ent_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # 3. ÁREA DE CONVERSA (CENTER)
        txt_conversa = scrolledtext.ScrolledText(chat_win, font=("Arial", 10), bg="#f9f9f9", wrap=tk.WORD)
        txt_conversa.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        txt_conversa.insert(tk.END, "SISTEMA: Conectado ao Especialista Matemático Sênior.\nPronto para análises preditivas estocásticas.\n\n")

        def enviar_msg():
            pergunta = ent_msg.get().strip()
            if not pergunta: return
            ent_msg.delete(0, tk.END)
            txt_conversa.insert(tk.END, f"VOCÊ: {pergunta}\n")
            txt_conversa.see(tk.END)
            
            def thread_task():
                resposta = self.brain.interagir_hibrido(pergunta)
                self.root.after(0, lambda: txt_conversa.insert(tk.END, f"IA: {resposta}\n\n"))
                self.root.after(0, lambda: txt_conversa.see(tk.END))
            
            threading.Thread(target=thread_task, daemon=True).start()

        ent_msg.bind("<Return>", lambda e: enviar_msg())
        tk.Button(frame_input, text="ENVIAR", command=enviar_msg, bg="#e1f5fe", width=12).pack(side=tk.RIGHT)

    def _popula_modelos(self, lb, token):
        lb.delete(0, tk.END)
        modelos = self.brain.listar_modelos_gemini(token)
        if not modelos:
            messagebox.showwarning("Aviso", "Nenhum modelo encontrado. Verifique seu token e conexão de internet.")
            return
        for m in modelos:
            lb.insert(tk.END, m)
            if m == self.brain.model_name: lb.select_set(lb.size()-1)

    def atualizar_hardware_status(self):
        if self.brain:
            self.canvas_cpu.itemconfig(self.led_cpu, fill="green")
            self.canvas_gpu.itemconfig(self.led_gpu, fill="green" if self.brain.verificar_saude_gpu() else "red")
        self.root.after(3000, self.atualizar_hardware_status)

    def set_brain(self, b): self.brain = b; self.atualizar_hardware_status()
    def _acao_segura(self, f):
        def r():
            try: f()
            except Exception as e: print(f"Erro: {e}")
        threading.Thread(target=r, daemon=True).start()

    def solicitar_simulacao(self):
        q = simpledialog.askinteger("Simulação", "Qtd cenários:", initialvalue=1000000)
        if q: self._acao_segura(lambda: self.brain.simular_cenarios(q, self.atualizar_barra_progresso))

    def atualizar_barra_progresso(self, a, t):
        self.progress['maximum'] = t; self.progress['value'] = a; self.root.update_idletasks()

    def solicitar_conferencia(self):
        e = simpledialog.askstring("Resultado", "Números (espaço ou hífen):")
        if e:
            try:
                # Normaliza a entrada substituindo hífens por espaços
                e_normalizada = e.replace('-', ' ')
                nums = [int(x) for x in e_normalizada.split() if x.isdigit()]
                if len(nums) >= 6: self._acao_segura(lambda: self.brain.conferir_resultado(nums[:6]))
            except: pass

    def importar_padrao(self):
        escolha = messagebox.askyesnocancel(
            "Método de Importação",
            "Deseja importar de um ARQUIVO (Sim)\nou DIGITAR dezenas manualmente (Não)?\n(Cancelar para sair)"
        )
        
        if escolha is True: # Arquivo
            arquivo = filedialog.askopenfilename(
                title="Selecionar Jogos Reais",
                filetypes=[("Arquivos de Dados", "*.xlsx *.csv"), ("Todos os arquivos", "*.*")]
            )
            from importar_dados import importar_dados
            if arquivo:
                self._acao_segura(lambda: importar_dados(arquivo, self.atualizar_barra_progresso))
            else:
                if messagebox.askyesno("Importação", "Nenhum arquivo selecionado. Deseja baixar a base oficial?"):
                    self._acao_segura(lambda: importar_dados(None, self.atualizar_barra_progresso))
        
        elif escolha is False: # Manual
            ultimo = self.brain.db_manager.obter_ultimo_sorteio()
            prox_conc = (ultimo['concurso'] + 1) if ultimo else 1
            
            msg = f"Lançando Concurso {prox_conc}\n\nDigite as 6 dezenas (espaço ou hífen):"
            entrada = simpledialog.askstring("Importação Manual Inteligente", msg)
            
            if entrada:
                try:
                    # Normaliza a entrada substituindo hífens por espaços
                    entrada_normalizada = entrada.replace('-', ' ')
                    nums = [int(x) for x in entrada_normalizada.split() if x.isdigit()]
                    if len(nums) >= 6:
                        # Chama a lógica do brain que já salva e atualiza o Excel de forma inteligente
                        self._acao_segura(lambda: self.brain.conferir_resultado(nums[:6]))
                        messagebox.showinfo("Sucesso", f"Concurso {prox_conc} adicionado e Excel atualizado!")
                    else:
                        messagebox.showwarning("Erro", "Digite pelo menos 6 números válidos.")
                except Exception as e:
                    messagebox.showerror("Erro", f"Falha ao processar entrada: {e}")

    def mostrar_jogos_elite(self):
        """Exibe os 4 jogos de elite calculados pela última simulação."""
        jogos = self.brain.jogos_elite
        if not jogos:
            messagebox.showwarning("Aviso", "Execute uma 'Simulação Monte Carlo' primeiro para habilitar estes jogos.")
            return
        
        msg = "4 JOGOS DE ELITE (Filtro Estocástico):\n\n"
        for i, jogo in enumerate(jogos):
            msg += f"Jogo {i+1}: {jogo}\n"
            
        msg += f"\nEstes jogos foram compostos a partir das 15 dezenas que mais 'performaram' na simulação de {self.progress['maximum']:,} cenários."
        messagebox.showinfo("Elite Math", msg)
        for i, jogo in enumerate(jogos):
            print(f"Elite: Sugestão {i+1}: {jogo}")

    def solicitar_grafico_frequencia(self):
        """Inicia o cálculo em thread e renderiza na principal."""
        def callback(d, f):
            self.root.after(0, lambda: self.brain._renderizar_grafico_interno(d, f))
        
        threading.Thread(target=lambda: self.brain.gerar_grafico_frequencia(callback), daemon=True).start()

    def alternar_tema(self):
        self.dark_mode = not self.dark_mode
        c = "#2e2e2e" if self.dark_mode else "white"
        self.log_area.config(bg=c, fg="white" if self.dark_mode else "black")

    def limpar_tela(self): self.log_area.delete(1.0, tk.END)
    def run(self): self.root.mainloop()
