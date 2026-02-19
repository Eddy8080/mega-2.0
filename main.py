import sys
import os
import json
from brain import Brain
from interface import Interface


# Caminho absoluto para o arquivo de configuração
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def carregar_configuracao():
    """Carrega o token e configurações do arquivo JSON."""
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
            return config
    except FileNotFoundError:
        print(f"Erro: Arquivo de configuração não encontrado em {CONFIG_PATH}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Erro: Falha ao ler o arquivo config.json")
        sys.exit(1)

def main():
    # 1. Inicializar Interface
    interface = Interface()

    # 2. Carregar Configurações
    config = carregar_configuracao()
    token = config.get("GEMINI_API_TOKEN")
    delay = config.get("API_DELAY_SECONDS", 2)
    
    if not token or token == "INSIRA_SEU_TOKEN_AQUI":
        interface.exibir_alerta("Token do Gemini não configurado.")
        interface.solicitar_token()
        # Tenta recarregar após a inserção do usuário
        config = carregar_configuracao()
        token = config.get("GEMINI_API_TOKEN")
        if not token or token == "INSIRA_SEU_TOKEN_AQUI":
            interface.exibir_mensagem("O sistema funcionará apenas com a IA Local por enquanto.")
    
    try:
        sistema_brain = Brain(api_token=token, api_delay=delay)
        # Conectar o cérebro à interface gráfica
        interface.set_brain(sistema_brain)
    except Exception as e:
        interface.exibir_alerta(f"Erro crítico ao iniciar o Brain: {e}")
        sys.exit(1)

    # 3. Iniciar Interface Gráfica
    interface.run()

if __name__ == "__main__":
    main()