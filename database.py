import sqlite3
import os

class DatabaseManager:
    """
    Gerencia a conexão com o banco de dados SQLite e a persistência dos sorteios.
    """
    def __init__(self, db_name="mega_sena.db"):
        # Define o caminho do banco de dados no mesmo diretório do script
        self.db_path = os.path.join(os.path.dirname(__file__), db_name)
        self.create_tables()

    def get_connection(self):
        """Estabelece e retorna uma conexão com o banco de dados."""
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        """Cria a tabela de sorteios se ela não existir."""
        query_sorteios = """
        CREATE TABLE IF NOT EXISTS sorteios (
            concurso INTEGER PRIMARY KEY,
            data_sorteio TEXT,
            bola1 INTEGER,
            bola2 INTEGER,
            bola3 INTEGER,
            bola4 INTEGER,
            bola5 INTEGER,
            bola6 INTEGER
        );
        """
        query_memoria = """
        CREATE TABLE IF NOT EXISTS memoria_ia (
            pergunta TEXT PRIMARY KEY,
            resposta TEXT
        );
        """
        query_estatisticas = """
        CREATE TABLE IF NOT EXISTS estatisticas_importadas (
            tipo TEXT,
            dado JSON,
            data_importacao TEXT
        );
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query_sorteios)
                cursor.execute(query_memoria)
                cursor.execute(query_estatisticas)
                conn.commit()
        except sqlite3.Error as e:
            print(f"Erro ao criar tabelas no banco de dados: {e}")

    def salvar_sorteio(self, concurso, data, numeros):
        """Salva ou atualiza um sorteio no banco de dados."""
        if len(numeros) != 6:
            raise ValueError("A lista de números deve conter exatamente 6 dezenas.")
        
        query = """
        INSERT OR REPLACE INTO sorteios (concurso, data_sorteio, bola1, bola2, bola3, bola4, bola5, bola6)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (concurso, data, *numeros))
            conn.commit()

    def obter_ultimo_sorteio(self):
        """Retorna o último sorteio cadastrado."""
        query = "SELECT concurso, data_sorteio, bola1, bola2, bola3, bola4, bola5, bola6 FROM sorteios ORDER BY concurso DESC LIMIT 1"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            if row:
                return {
                    'concurso': row[0],
                    'data': row[1],
                    'numeros': [row[2], row[3], row[4], row[5], row[6], row[7]]
                }
            return None

    def obter_todos_sorteios(self):
        """Retorna todos os sorteios ordenados por concurso (decrescente)."""
        query = "SELECT concurso, bola1, bola2, bola3, bola4, bola5, bola6 FROM sorteios ORDER BY concurso DESC"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()

    def buscar_memoria(self, pergunta):
        """Busca uma resposta na memória de longo prazo."""
        query = "SELECT resposta FROM memoria_ia WHERE pergunta = ?"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pergunta.strip().lower(),))
            row = cursor.fetchone()
            return row[0] if row else None

    def salvar_memoria(self, pergunta, resposta):
        """Salva um novo conhecimento na memória de longo prazo."""
        query = "INSERT OR REPLACE INTO memoria_ia (pergunta, resposta) VALUES (?, ?)"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (pergunta.strip().lower(), resposta))
            conn.commit()

    def salvar_estatistica(self, tipo, dados_json):
        """Salva um bloco de estatísticas importadas."""
        import datetime
        hoje = datetime.datetime.now().isoformat()
        query = "INSERT INTO estatisticas_importadas (tipo, dado, data_importacao) VALUES (?, ?, ?)"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (tipo, dados_json, hoje))
            conn.commit()

    def limpar_memoria(self):
        """Apaga todo o conhecimento da memória de longo prazo."""
        query = "DELETE FROM memoria_ia"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()

    def obter_toda_memoria(self):
        """Retorna todo o conhecimento salvo na memória."""
        query = "SELECT pergunta, resposta FROM memoria_ia"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()

    def verificar_integridade(self):
        """Verifica a integridade do banco de dados e estrutura."""
        try:
            if not os.path.exists(self.db_path):
                self.create_tables()
                return True, "Banco de dados não existia e foi criado com sucesso."

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                
                # Garante que as tabelas existem (correção estrutural)
                self.create_tables()
                
                if result and result[0] == 'ok':
                    return True, "Integridade do arquivo: OK. Estrutura de tabelas validada."
                else:
                    return False, f"Corrupção detectada no arquivo: {result[0]}"
        except Exception as e:
            return False, f"Erro durante verificação: {e}"