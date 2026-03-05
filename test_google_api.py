import os
import json

try:
    # Tenta importar a biblioteca oficial do Google
    from google import genai
    print("Biblioteca 'google-genai' encontrada.")
except ImportError:
    print("\nERRO: A biblioteca 'google-genai' não está instalada.")
    print("Por favor, execute no terminal: pip install google-genai\n")
    exit()

# Tenta importar utilitário de segurança para ler config.json do projeto
try:
    from security_utils import SecurityHandler
except ImportError:
    SecurityHandler = None


def testar_conexao_google_api():
    """
    Script de teste isolado para validar a conexão com a API do Google Gemini.
    """
    print("\n--- Teste de Conexão com a API do Google Gemini ---")

    # --- PASSO 1: Insira sua chave de API aqui ---
    # Obtenha sua chave em: https://aistudio.google.com/app/apikey
    # Substitua 'SUA_API_KEY_AQUI' pela chave que começa com 'AIza...'
    GOOGLE_API_KEY = ''

    # Tenta carregar automaticamente do config.json se estiver vazio
    if not GOOGLE_API_KEY and os.path.exists("config.json") and SecurityHandler:
        try:
            with open("config.json", "r") as f:
                cfg = json.load(f)
                enc_key = cfg.get("inteligencia_artificial",
                                  {}).get("api_key", "")
                if enc_key:
                    GOOGLE_API_KEY = SecurityHandler.decrypt_text(enc_key)
                    print("ℹ️ Chave de API carregada automaticamente do 'config.json'.")
        except Exception:
            pass

    if not GOOGLE_API_KEY or GOOGLE_API_KEY == 'SUA_API_KEY_AQUI':
        print("\n❌ ERRO: Chave de API não encontrada.")
        print("Edite o arquivo 'google.py' e preencha a variável GOOGLE_API_KEY, ou configure na Interface.")
        return

    try:
        print("Configurando cliente com a chave de API...")
        client = genai.Client(api_key=GOOGLE_API_KEY)

        # --- DIAGNÓSTICO DE MODELOS ---
        print("\nVerificando modelos disponíveis para sua chave...")
        model_list = []
        try:
            # Lista modelos para ver quais a chave tem acesso
            pager = client.models.list()
            print("Modelos encontrados:")
            # Iteração simplificada para evitar erros de atributos na nova versão do SDK
            for model in pager:
                # Filtra apenas modelos 'gemini' para facilitar a leitura
                if 'gemini' in model.name:
                    print(f" - {model.name}")
                    model_list.append(model.name)
        except Exception as e:
            print(f"⚠️ Não foi possível listar modelos: {e}")
            return
        # ------------------------------

        # --- TESTE EM LOTE ---
        print("\n--- Iniciando teste de conexão para cada modelo Gemini ---")
        if not model_list:
            print("Nenhum modelo Gemini encontrado para testar.")
            return

        for model_name in model_list:
            print(f"\n--- Testando: {model_name} ---")
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents="Responda 'OK' se a conexão funcionar."
                )
                print(f"✅ SUCESSO! Resposta: {response.text.strip()}")
            except Exception as e:
                error_message = str(e)
                if "429" in error_message:
                    print("❌ FALHA: Cota de uso excedida (RESOURCE_EXHAUSTED).")
                elif "404" in error_message:
                    print(
                        "❌ FALHA: Modelo não encontrado ou não suporta 'generateContent' (NOT_FOUND).")
                else:
                    print(f"❌ FALHA: Erro inesperado. Detalhes: {e}")

    except Exception as e:
        print(f"\n❌ FALHA! Erro ao conectar com a API do Google:")
        print(f"   Detalhes: {e}")


if __name__ == "__main__":
    testar_conexao_google_api()
