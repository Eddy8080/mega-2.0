import sys
import os
import json
from brain import Brain
from interface import Interface

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')

def carregar_configuracao():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'w') as f:
            json.dump({"GEMINI_API_TOKEN": "INSIRA_SEU_TOKEN_AQUI", "GEMINI_MODEL": "gemini-2.0-flash", "API_DELAY_SECONDS": 2}, f)
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except:
        return {"GEMINI_API_TOKEN": "INSIRA_SEU_TOKEN_AQUI", "GEMINI_MODEL": "gemini-2.0-flash", "API_DELAY_SECONDS": 2}

def main():
    interface = Interface()
    config = carregar_configuracao()
    
    token = config.get("GEMINI_API_TOKEN")
    delay = config.get("API_DELAY_SECONDS", 2)

    try:
        # Inicializa o cérebro (ele lidará internamente se o token é válido ou não)
        sistema_brain = Brain(api_token=token, api_delay=delay)
        interface.set_brain(sistema_brain)
    except Exception as e:
        print(f"Erro crítico: {e}")
        sys.exit(1)

    interface.run()

if __name__ == "__main__":
    main()
