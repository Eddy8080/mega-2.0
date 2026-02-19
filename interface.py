import os
import sys
import json
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, filedialog, ttk


class TextRedirector:
    """Classe utilitária para redirecionar o stdout (print) para o widget de texto."""

    def __init__(self, widget):
        self.widget = widget

    def write(self, str):
        self.widget.insert("end", str)
        self.widget.see("end")
        self.widget.update_idletasks()

    def flush(self):
        pass


class ToolTip(object):
    """
    Cria um tooltip para um widget específico.
    """

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + cy + self.widget.winfo_rooty() + 25
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


class Interface:
    """
    Classe responsável por toda a interação com o usuário (GUI).
    """

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sistema Híbrido Mega-Sena")
        self.root.geometry("1000x800")
        self.brain = None
        self.dark_mode = False
        self.config_path = os.path.join(
            os.path.dirname(__file__), 'config.json')

        self._configurar_ui()

        # Redirecionar prints para a tela
        sys.stdout = TextRedirector(self.log_area)

    def _configurar_ui(self):
        # Frame Principal da Esquerda (Container)
        self.frame_esquerda = tk.Frame(self.root)
        self.frame_esquerda.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # 1. Área Fixa Inferior (Sair, Config, Status)
        self.frame_inferior = tk.Frame(self.frame_esquerda)
        self.frame_inferior.pack(side=tk.BOTTOM, fill=tk.X)

        # Botão Sair
        btn_sair = tk.Button(self.frame_inferior, text="Sair",
                             command=self.root.quit, bg="#ffcccc")
        btn_sair.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        # Botão Config Token
        btn_config = tk.Button(
            self.frame_inferior, text="Config. Token", command=self.solicitar_token)
        btn_config.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        # Frame para Status da GPU
        self.frame_gpu = tk.Frame(self.frame_inferior)
        self.frame_gpu.pack(side=tk.BOTTOM, fill=tk.X, pady=2)

        self.canvas_gpu = tk.Canvas(
            self.frame_gpu, width=20, height=20, highlightthickness=0)
        self.canvas_gpu.pack(side=tk.LEFT, padx=2)
        self.led_gpu = self.canvas_gpu.create_oval(
            4, 4, 16, 16, fill="gray", outline="gray")

        self.lbl_gpu_text = tk.Label(
            self.frame_gpu, text="GPU: ...", font=("Arial", 8))
        self.lbl_gpu_text.pack(side=tk.LEFT)

        # Frame para Status da API (LED + Texto)
        self.frame_status = tk.Frame(self.frame_inferior)
        self.frame_status.pack(side=tk.BOTTOM, fill=tk.X, pady=2)

        self.canvas_status = tk.Canvas(
            self.frame_status, width=20, height=20, highlightthickness=0, cursor="hand2")
        self.canvas_status.pack(side=tk.LEFT, padx=2)
        self.led_status = self.canvas_status.create_oval(
            4, 4, 16, 16, fill="gray", outline="gray")

        # Tooltip para o status
        self.tooltip_status = ToolTip(self.canvas_status)
        self.canvas_status.bind("<Enter>", self._mostrar_tooltip_status)
        self.canvas_status.bind(
            "<Leave>", lambda e: self.tooltip_status.hidetip())

        self.lbl_status_text = tk.Label(
            self.frame_status, text="Verificando...", font=("Arial", 8), cursor="hand2")
        self.lbl_status_text.pack(side=tk.LEFT)

        # Bind de clique para Ping manual
        self.canvas_status.bind(
            "<Button-1>", lambda e: self.verificar_conexao_manual())
        self.lbl_status_text.bind(
            "<Button-1>", lambda e: self.verificar_conexao_manual())

        # Label Contador de Tokens (Acima do Config Token)
        self.lbl_tokens = tk.Label(
            self.frame_inferior, text="Cota Diária: 0/1500", font=("Arial", 9, "bold"))
        self.lbl_tokens.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        # 2. Área Rolável Superior (Lista de Botões)
        self.frame_canvas = tk.Frame(self.frame_esquerda)
        self.frame_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(self.frame_canvas, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.frame_canvas, orient="vertical", command=self.canvas.yview)
        
        self.frame_botoes_scroll = tk.Frame(self.canvas)

        self.frame_botoes_scroll.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.frame_botoes_scroll, anchor="nw")
        
        def on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        
        self.canvas.bind("<Configure>", on_canvas_configure)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Mousewheel scrolling
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Lista de botões organizada por categorias
        categorias = [
            ("Gestão de Dados", [
                ("Inserir mega_sena.xlsx", self.importar_padrao),
                ("Selecionar Arquivo...", self.importar_dados_dialog),
                ("Abrir Excel", lambda: self._acao_segura(self.brain.abrir_arquivo_excel)),
                ("Check Integridade", lambda: self._acao_segura(self.brain.verificar_integridade_banco)),
                ("Backup DB", lambda: self._acao_segura(self.brain.fazer_backup)),
                ("Restaurar DB", self.restaurar_backup_dialog),
                ("Limpar Tela", self.limpar_tela),
            ]),
            ("Análises Estatísticas", [
                ("2. Simulação", self.solicitar_simulacao),
                ("Comp. Simulação", lambda: self._acao_segura(self.brain.comparar_simulacao_realidade)),
                ("3. Conferência", self.solicitar_conferencia),
                ("4. Teste GPU", lambda: self._acao_segura(self.brain.exemplo_gpu)),
                ("Benchmark CPU/GPU", lambda: self._acao_segura(self.brain.benchmark_cpu_vs_gpu)),
                ("5. Atrasos", lambda: self._acao_segura(self.brain.analisar_atrasos)),
                ("6. Par/Ímpar", lambda: self._acao_segura(self.brain.analisar_pares_impares)),
                ("8. Quadrantes", lambda: self._acao_segura(self.brain.analisar_quadrantes)),
                ("10. Linhas/Colunas", lambda: self._acao_segura(self.brain.analisar_linhas_colunas)),
                ("11. Primos", lambda: self._acao_segura(self.brain.analisar_numeros_primos)),
                ("Primos Gêmeos", lambda: self._acao_segura(self.brain.analisar_primos_gemeos)),
                ("Fibonacci", lambda: self._acao_segura(self.brain.analisar_fibonacci)),
                ("Múltiplos de 3", lambda: self._acao_segura(self.brain.analisar_multiplos_de_3)),
                ("12. Soma", lambda: self._acao_segura(self.brain.analisar_soma_dezenas)),
                ("Gêmeas", lambda: self._acao_segura(self.brain.analisar_dezenas_gemeas)),
                ("Invertidas", lambda: self._acao_segura(self.brain.analisar_dezenas_invertidas)),
                ("Números Espelho", lambda: self._acao_segura(self.brain.analisar_numeros_espelho)),
                ("Pares Viciados", lambda: self._acao_segura(self.brain.analisar_pares_viciados)),
                ("Trincas", lambda: self._acao_segura(self.brain.analisar_trincas)),
                ("Vizinhas", lambda: self._acao_segura(self.brain.analisar_dezenas_vizinhas)),
                ("Intervalos (Gaps)", lambda: self._acao_segura(self.brain.analisar_intervalos)),
                ("Quadras", lambda: self._acao_segura(self.brain.analisar_quadras)),
                ("Quinas", lambda: self._acao_segura(self.brain.analisar_quinas)),
                ("Senas Repetidas", lambda: self._acao_segura(self.brain.analisar_senas_repetidas)),
                ("Temperatura", lambda: self._acao_segura(self.brain.analisar_temperatura)),
                ("13. Finais", lambda: self._acao_segura(self.brain.analisar_finais)),
                ("15. Ciclos", lambda: self._acao_segura(self.brain.analisar_ciclos)),
                ("16. Sequências", lambda: self._acao_segura(self.brain.analisar_sequencias)),
                ("17. Gráfico Freq.", lambda: self._acao_segura(self.brain.gerar_grafico_frequencia)),
                ("Heatmap Correlação", lambda: self._acao_segura(self.brain.gerar_heatmap_correlacao)),
                ("18. Sazonalidade", lambda: self._acao_segura(self.brain.analisar_meses)),
            ]),
            ("Ferramentas e Cálculos", [
                ("Calc. Custo", self.solicitar_calculo_custo),
                ("Simular Gastos", self.solicitar_simulacao_gastos),
                ("9. Desdobramento", lambda: self._acao_segura(self.brain.explicar_desdobramento)),
            ]),
            ("Inteligência Artificial", [
                ("7. Análise IA", lambda: self._acao_segura(self.brain.analisar_ia_repeticoes)),
                ("14. Palpite IA", lambda: self._acao_segura(self.brain.gerar_palpite_ia)),
                ("Chat Híbrido", self.solicitar_chat_hibrido),
                ("Limpar Memória IA", self.solicitar_limpeza_memoria),
                ("Exportar Memória IA", self.exportar_memoria_ia_dialog),
                ("Analisar Qualidade Memória", lambda: self._acao_segura(self.brain.analisar_qualidade_memoria)),
                ("Refinar Memória", lambda: self._acao_segura(self.brain.refinar_memoria_ia)),
            ]),
            ("Relatórios", [
                ("Gerar PDF Completo", self.gerar_relatorio_pdf_dialog),
                ("Exportar Relatório", self.exportar_relatorio),
            ]),
            ("Sistema", [
                ("Modo Escuro", self.alternar_tema),
            ]),
            ("Geração Final", [
                ("Abrir Meus Jogos", lambda: self._acao_segura(self.brain.abrir_meus_jogos)),
                ("1. Inteligência (Gerar)", lambda: self._acao_segura(self.brain.pensar_jogos)),
            ]),
        ]

        for nome_cat, lista_btns in categorias:
            lf = tk.LabelFrame(self.frame_botoes_scroll, text=nome_cat, font=("Arial", 9, "bold"))
            lf.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5, ipadx=2, ipady=2)
            for texto, comando in lista_btns:
                btn = tk.Button(lf, text=texto, command=comando)
                btn.pack(side=tk.TOP, fill=tk.X, pady=2, padx=2)

        # Barra de Progresso (Adicionada na parte inferior da área principal)
        self.progress = ttk.Progressbar(
            self.root, orient="horizontal", length=100, mode="determinate")
        self.progress.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Área de Log/Texto
        self.log_area = scrolledtext.ScrolledText(
            self.root, state='normal', font=("Consolas", 10))
        self.log_area.pack(side=tk.RIGHT, expand=True,
                           fill='both', padx=10, pady=10)
        # Bloquear edição do usuário, mas permitir seleção e cópia (Ctrl+C)
        self.log_area.bind("<Key>", self._bloquear_edicao)

    def set_brain(self, brain_instance):
        """Conecta a instância do Brain à interface."""
        self.brain = brain_instance
        self.atualizar_status_api()
        self.atualizar_tokens()
        self.atualizar_status_gpu()

    def _acao_segura(self, func):
        """Executa uma função do brain garantindo que ele exista."""
        if self.brain:
            self.limpar_tela()
            func()
        else:
            self.exibir_alerta(
                "O módulo 'Brain' não foi inicializado corretamente.")
        self.atualizar_tokens()
        self.atualizar_status_api()
        self.atualizar_status_gpu()

    def _bloquear_edicao(self, event):
        """Impede a edição do texto, mas permite cópia e navegação."""
        # Permitir Ctrl+C (Copy) e Ctrl+A (Select All)
        if (event.state & 4) and (event.keysym.lower() in ['c', 'a']):
            return None
        # Permitir teclas de navegação
        if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Home', 'End', 'Prior', 'Next']:
            return None
        return "break"

    def run(self):
        """Inicia o loop principal da interface gráfica."""
        self.exibir_mensagem("Sistema Híbrido Mega-Sena Inicializado.")
        self.exibir_mensagem("Aguardando comandos...")
        self.root.mainloop()

    def limpar_tela(self):
        self.log_area.delete(1.0, tk.END)

    def exibir_mensagem(self, mensagem):
        print(f"> {mensagem}")

    def exibir_alerta(self, mensagem):
        messagebox.showwarning("Alerta do Sistema", mensagem)

    def solicitar_token(self):
        """Abre um diálogo para o usuário inserir o token e salva no JSON."""
        token = simpledialog.askstring(
            "Configuração", "Insira o Token do Gemini (Google AI Studio):", show='*')
        if token:
            self.salvar_token(token)

    def salvar_token(self, token):
        try:
            config = {}
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    try:
                        config = json.load(f)
                    except json.JSONDecodeError:
                        pass
            config["GEMINI_API_TOKEN"] = token
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            self.exibir_mensagem(
                "Token salvo com sucesso! As alterações terão efeito imediato ou no próximo reinício.")
        except Exception as e:
            self.exibir_alerta(f"Erro ao salvar token: {e}")

    def solicitar_simulacao(self):
        """Solicita a quantidade de simulações ao usuário."""
        qtd = simpledialog.askinteger(
            "Simulação Monte Carlo", "Quantidade de cenários (Ex: 1000000):", 
            minvalue=1000, maxvalue=100_000_000, initialvalue=1_000_000)
        if qtd:
            self._acao_segura(lambda: self.brain.simular_cenarios(qtd))

    def solicitar_conferencia(self):
        """Solicita os números ao usuário e envia para conferência."""
        entrada = simpledialog.askstring(
            "Conferência", "Digite os números da aposta (separados por vírgula):")
        if not entrada:
            return

        try:
            # Converte string "1, 2, 3" para lista de inteiros [1, 2, 3]
            numeros = [int(n.strip()) for n in entrada.split(',')]
            if any(n < 1 or n > 60 for n in numeros):
                raise ValueError("Os números devem estar entre 1 e 60.")

            self._acao_segura(lambda: self.brain.conferir_resultado(numeros))
        except ValueError:
            self.exibir_alerta(
                "Entrada inválida! Digite apenas números entre 1 e 60 separados por vírgula.")

    def exportar_relatorio(self):
        """Salva o histórico da sessão (log) em um arquivo de texto."""
        conteudo = self.log_area.get("1.0", tk.END)
        if not conteudo.strip():
            self.exibir_alerta("Não há dados para exportar.")
            return

        arquivo = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivo de Texto", "*.txt"),
                       ("Todos os Arquivos", "*.*")],
            title="Salvar Relatório"
        )

        if arquivo:
            try:
                with open(arquivo, 'w', encoding='utf-8') as f:
                    f.write(conteudo)
                self.exibir_mensagem(
                    f"Relatório salvo com sucesso em: {arquivo}")
            except Exception as e:
                self.exibir_alerta(f"Erro ao salvar relatório: {e}")

    def restaurar_backup_dialog(self):
        """Abre diálogo para selecionar backup e chama o brain."""
        arquivo = filedialog.askopenfilename(
            filetypes=[("Banco de Dados SQLite", "*.db"),
                       ("Todos os Arquivos", "*.*")],
            title="Selecionar Backup para Restaurar",
            initialdir=os.path.join(os.path.dirname(__file__), 'backups')
        )

        if arquivo:
            confirmacao = messagebox.askyesno(
                "Confirmar Restauração",
                "Isso substituirá o banco de dados atual pelo backup selecionado.\nTem certeza?"
            )
            if confirmacao:
                self._acao_segura(lambda: self.brain.restaurar_backup(arquivo))

    def importar_dados_dialog(self):
        """Abre diálogo para selecionar arquivo de dados (CSV/Excel)."""
        arquivo = filedialog.askopenfilename(
            filetypes=[("Arquivos de Dados", "*.csv *.xlsx"),
                       ("Todos os Arquivos", "*.*")],
            title="Selecionar Arquivo de Sorteios"
        )
        if arquivo:
            self.progress['value'] = 0  # Resetar barra
            self._acao_segura(lambda: self.brain.atualizar_base_dados(
                arquivo, self.atualizar_barra_progresso))

    def importar_padrao(self):
        """Importa do arquivo padrão mega_sena.xlsx."""
        self.progress['value'] = 0
        self._acao_segura(lambda: self.brain.atualizar_base_dados(
            None, self.atualizar_barra_progresso))

    def atualizar_barra_progresso(self, atual, total):
        """Atualiza a barra de progresso."""
        self.progress['maximum'] = total
        self.progress['value'] = atual
        self.root.update_idletasks()

    def solicitar_calculo_custo(self):
        """Solicita a quantidade de números e calcula o custo."""
        qtd = simpledialog.askinteger(
            "Calculadora de Custo", "Quantos números na aposta? (6-20):", minvalue=6, maxvalue=20)
        if qtd:
            self._acao_segura(lambda: self.brain.calcular_custo_aposta(qtd))

    def solicitar_simulacao_gastos(self):
        """Solicita o orçamento e simula gastos."""
        valor = simpledialog.askfloat(
            "Simulação de Gastos", "Qual o seu orçamento? (R$)", minvalue=6.0)
        if valor:
            self._acao_segura(lambda: self.brain.simular_gastos(valor))

    def solicitar_chat_hibrido(self):
        """Abre chat para interação híbrida (Memória + IA)."""
        pergunta = simpledialog.askstring(
            "Chat Híbrido", "Faça uma pergunta sobre a Mega-Sena ou estatísticas:")
        if pergunta:
            self._acao_segura(lambda: self.brain.interagir_hibrido(pergunta))

    def solicitar_limpeza_memoria(self):
        """Solicita confirmação para limpar a memória da IA."""
        confirmacao = messagebox.askyesno(
            "Limpar Memória IA",
            "Tem certeza que deseja apagar todo o conhecimento aprendido pela IA?\nIsso não pode ser desfeito."
        )
        if confirmacao:
            self._acao_segura(lambda: self.brain.limpar_memoria_ia())

    def exportar_memoria_ia_dialog(self):
        """Abre diálogo para exportar a memória da IA."""
        arquivo = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Arquivo JSON", "*.json"), ("Todos os Arquivos", "*.*")],
            title="Exportar Memória da IA"
        )
        if arquivo:
            self._acao_segura(lambda: self.brain.exportar_memoria_ia(arquivo))

    def gerar_relatorio_pdf_dialog(self):
        """Abre diálogo para gerar relatório PDF."""
        arquivo = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("Arquivo PDF", "*.pdf"), ("Todos os Arquivos", "*.*")],
            title="Salvar Relatório PDF"
        )
        if arquivo:
            self._acao_segura(lambda: self.brain.gerar_relatorio_pdf(arquivo))

    def alternar_tema(self):
        """Alterna entre modo claro e escuro."""
        self.dark_mode = not self.dark_mode

        if self.dark_mode:
            bg_color = "#2e2e2e"
            fg_color = "#ffffff"
            txt_bg = "#1e1e1e"
            txt_fg = "#00ff00"
            btn_bg = "#444444"
            lbl_bg = "#2e2e2e"
            status_bg = "#2e2e2e"
        else:
            bg_color = "#f0f0f0"
            fg_color = "#000000"
            txt_bg = "#ffffff"
            txt_fg = "#000000"
            btn_bg = "#f0f0f0"
            lbl_bg = "#f0f0f0"
            status_bg = "#f0f0f0"

        self.root.configure(bg=bg_color)
        self.log_area.configure(bg=txt_bg, fg=txt_fg)
        self.lbl_tokens.configure(bg=lbl_bg, fg=fg_color)

        self.frame_status.configure(bg=status_bg)
        self.canvas_status.configure(bg=status_bg)
        self.lbl_status_text.configure(bg=status_bg, fg=fg_color)
        
        self.frame_gpu.configure(bg=status_bg)
        self.canvas_gpu.configure(bg=status_bg)
        self.lbl_gpu_text.configure(bg=status_bg, fg=fg_color)

        # Atualiza frame e botões
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame):
                widget.configure(bg=bg_color)
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button):
                        if child['text'] == "Sair":
                            child.configure(
                                bg="#880000" if self.dark_mode else "#ffcccc", fg=fg_color)
                        else:
                            child.configure(bg=btn_bg, fg=fg_color)

                        if child['text'] in ["Modo Escuro", "Modo Claro"]:
                            child.configure(
                                text="Modo Claro" if self.dark_mode else "Modo Escuro")

    def atualizar_tokens(self):
        """Atualiza o contador de tokens na interface."""
        if self.brain:
            uso, limite = self.brain.obter_cota_atual()
            self.lbl_tokens.config(text=f"Cota Diária: {uso}/{limite}")

    def atualizar_status_gpu(self):
        """Atualiza o indicador visual (LED) do status da GPU."""
        if self.brain:
            ativo = self.brain.verificar_saude_gpu()
            cor = "#00ff00" if ativo else "gray"
            texto = "GPU: ON (CuPy)" if ativo else "GPU: OFF (CPU)"
            
            self.canvas_gpu.itemconfig(self.led_gpu, fill=cor, outline=cor)
            self.lbl_gpu_text.config(text=texto)

    def atualizar_status_api(self):
        """Atualiza o indicador visual (LED) do status da API."""
        if self.brain:
            status, texto = self.brain.obter_status_ia()
            cor = "gray"
            if status == "online":
                cor = "#00ff00"  # Verde
            elif status == "limitado":
                cor = "#ffaa00"  # Laranja/Amarelo
            elif status == "offline":
                cor = "#ff0000"  # Vermelho

            self.canvas_status.itemconfig(
                self.led_status, fill=cor, outline=cor)
            self.lbl_status_text.config(text=texto)

    def verificar_conexao_manual(self):
        """Força um teste de conexão (Ping) ao clicar no status."""
        if not self.brain:
            return

        self.lbl_status_text.config(text="Pingando...")
        self.canvas_status.itemconfig(
            self.led_status, fill="blue", outline="blue")
        self.root.update_idletasks()

        status, texto = self.brain.testar_conexao_api()

        cor = "gray"
        if status == "online":
            cor = "#00ff00"
        elif status == "limitado":
            cor = "#ffaa00"
        elif status == "offline":
            cor = "#ff0000"

        self.canvas_status.itemconfig(self.led_status, fill=cor, outline=cor)
        self.lbl_status_text.config(text=texto)

    def _mostrar_tooltip_status(self, event):
        """Exibe o tooltip com detalhes da conexão."""
        if not self.brain:
            return
        uso, limite = self.brain.obter_cota_atual()
        status, msg = self.brain.obter_status_ia()

        texto = f"Status: {status.upper()}\n" \
            f"Mensagem: {msg}\n" \
            f"Cota: {uso}/{limite}\n" \
            f"Delay API: {self.brain.api_delay}s"

        self.tooltip_status.showtip(texto)
