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
            raise ValueError(
                "A lista de números deve conter exatamente 6 dezenas.")

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

    def limpar_estatisticas_importadas(self):
        """Remove todas as estatísticas importadas do banco de dados."""
        query = "DELETE FROM estatisticas_importadas"
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
        """Verifica a integridade do arquivo, estrutura e realiza AUDITORIA das dezenas."""
        try:
            if not os.path.exists(self.db_path):
                self.create_tables()
                return True, "Banco de dados não existia. Novo arquivo criado e tabelas inicializadas."

            erros = []
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Integridade Física do SQLite
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()
                if not result or result[0] != 'ok':
                    erros.append(f"Erro físico no SQLite: {result[0]}")

                # 2. Garantir Estrutura de Tabelas
                self.create_tables()

                # 3. Auditoria Semântica dos Sorteios
                cursor.execute("SELECT concurso, bola1, bola2, bola3, bola4, bola5, bola6 FROM sorteios")
                rows = cursor.fetchall()
                
                if not rows:
                    return True, "Estrutura física OK, mas o banco de dados está vazio (sem sorteios para validar)."

                for row in rows:
                    conc = row[0]
                    dezenas = [d for d in row[1:] if d is not None]
                    
                    # Verificar se há dezenas faltando (devem ser 6)
                    if len(dezenas) != 6:
                        erros.append(f"Concurso {conc}: Contém apenas {len(dezenas)} dezenas (esperado: 6).")
                        continue
                    
                    # Verificar dezenas nulas ou zeradas
                    if any(v == 0 for v in dezenas):
                        erros.append(f"Concurso {conc}: Contém dezenas zeradas.")
                    
                    # Verificar se as dezenas estão entre 1 e 60
                    if any(v < 1 or v > 60 for v in dezenas):
                        erros.append(f"Concurso {conc}: Dezenas fora do intervalo 1-60 -> {dezenas}")
                    
                    # Verificar números repetidos no mesmo sorteio
                    if len(set(dezenas)) != 6:
                        erros.append(f"Concurso {conc}: Contém dezenas duplicadas -> {dezenas}")

            if erros:
                msg = f"Inconsistências detectadas ({len(erros)} erro(s)):\n"
                msg += "\n".join(erros[:10]) # Mostra os primeiros 10 erros
                if len(erros) > 10: msg += f"\n... e mais {len(erros)-10} erros."
                return False, msg
            
            return True, f"Integridade Total: OK.\n >> {len(rows)} sorteios auditados individualmente.\n >> Nenhuma duplicata ou dezena fora de range encontrada."

        except Exception as e:
            return False, f"Erro crítico durante a auditoria: {e}"
