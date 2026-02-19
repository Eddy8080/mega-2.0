# Análise de Requisitos e Documentação Técnica: Sistema Híbrido Mega-Sena

## 1. Visão Geral do Projeto
Sistema desktop desenvolvido em Python para análise estatística, simulação e geração de palpites para a Mega-Sena. O sistema opera em arquitetura híbrida, combinando algoritmos determinísticos (estatística clássica), simulações de Monte Carlo (probabilidade) e Inteligência Artificial Generativa (Google Gemini) com memória de longo prazo local.

A interface gráfica (GUI) permite ao usuário interagir com dados históricos, visualizar gráficos, gerenciar banco de dados e dialogar com a IA para obter insights estratégicos.

## 2. Arquitetura e Integrações
- **Interface Gráfica:** Construída com `tkinter`, oferecendo temas Claro/Escuro, logs em tempo real e indicadores de status (GPU/API).
- **Banco de Dados:** `SQLite` local para armazenamento de sorteios, estatísticas importadas e memória de aprendizado da IA.
- **Inteligência Artificial:**
    - Integração com **Google Gemini 2.0 Flash** via API (`google-genai`).
    - Sistema de **Cota Diária** local (limite de 1500 requisições/dia).
    - **Memória de Longo Prazo:** O sistema armazena perguntas e respostas úteis no banco de dados para evitar consumo desnecessário de tokens e criar uma base de conhecimento evolutiva.
- **Processamento de Alta Performance (HPC):**
    - Suporte a aceleração via GPU utilizando `CuPy` e `JAX`.
    - Fallback automático para CPU (`NumPy`) caso hardware compatível não seja detectado.

## 3. Funcionalidades Implementadas

### 3.1. Gestão de Dados
- **Importação Inteligente:** Capacidade de ler arquivos Excel (`.xlsx`) e CSV (`.csv`) com detecção dinâmica de colunas.
- **Download Automático:** Busca dataset público caso não haja arquivo local.
- **Backup e Restauração:** Ferramentas para backup do banco de dados SQLite e dos arquivos de dados brutos.
- **Verificação de Integridade:** Rotinas para validar a estrutura do banco de dados.

### 3.2. Análises Estatísticas (Módulo Brain)
O sistema realiza análises profundas sobre o histórico de sorteios:
- **Frequência e Atrasos:** Identificação de números "quentes" (mais sorteados) e "frios" (mais atrasados).
- **Padrões Numéricos:**
    - Par/Ímpar.
    - Números Primos e Primos Gêmeos.
    - Sequência de Fibonacci.
    - Múltiplos de 3.
- **Análise Espacial e Estrutural:**
    - Quadrantes (distribuição no volante).
    - Linhas e Colunas.
    - Dezenas Vizinhas e Intervalos (Gaps).
    - Dezenas Espelho e Invertidas.
- **Padrões de Repetição:**
    - Ciclos das dezenas (tempo para saírem todas as 60).
    - Sequências numéricas.
    - Senas repetidas (verificação histórica).
    - Trincas, Quadras e Quinas mais frequentes.
- **Temperatura:** Análise da soma das dezenas (média histórica).
- **Visualização:**
    - Gráficos de barras (Frequência).
    - Heatmaps de correlação entre dezenas.
    - Gráficos de linha (Temperatura/Soma).

### 3.3. Simulação e Probabilidade
- **Simulação de Monte Carlo:** Geração de milhões de cenários aleatórios para demonstrar a Lei dos Grandes Números e comparar a probabilidade teórica com a realidade histórica.
- **Benchmark de Hardware:** Teste comparativo de velocidade entre CPU e GPU para geração de números aleatórios.

### 3.4. Inteligência Artificial e Chat Híbrido
- **Palpite IA:** Geração de jogos baseados em prompt engenheirado com dados estatísticos atuais (quentes/frios).
- **Chat Híbrido:** Interface de chat onde a IA responde dúvidas sobre loteria. O sistema verifica primeiro a memória local; se não souber, consulta a API e aprende a resposta.
- **Refinamento de Memória:** Rotina para melhorar respostas curtas ou vagas armazenadas anteriormente.

### 3.5. Ferramentas e Relatórios
- **Calculadora de Custos:** Cálculo de preço para apostas múltiplas (6 a 20 números).
- **Simulador de Gastos:** Sugestão de estratégias (Volume vs Potência) baseada no orçamento do usuário.
- **Relatórios:**
    - Exportação de logs para `.txt`.
    - Geração de relatório completo em **PDF** com tabelas e gráficos estatísticos.
    - Exportação da memória da IA para `.json`.

## 4. Stack Tecnológica
- **Linguagem:** Python 3.x
- **Bibliotecas Principais:**
    - `tkinter`: Interface Gráfica.
    - `sqlite3`: Banco de Dados.
    - `pandas`: Manipulação de dados e importação.
    - `numpy`: Cálculos numéricos na CPU.
    - `cupy` / `jax`: Cálculos numéricos na GPU (Opcional).
    - `google-genai`: Cliente API Gemini.
    - `matplotlib`: Geração de gráficos.
    - `reportlab`: Geração de PDFs.
    - `openpyxl`: Leitura de Excel.

## 5. Estrutura de Arquivos
- **`interface.py`:** Gerencia a GUI, eventos do usuário e exibição de logs.
- **`brain.py`:** Contém a lógica de negócios, cálculos estatísticos, integração com IA e controle de hardware.
- **`database.py`:** Camada de persistência (SQLite).
- **`importar_dados.py`:** Scripts de ETL (Extract, Transform, Load) para dados de sorteios.
- **`config.json`:** Armazena token da API (gerado localmente).
- **`quota.json`:** Controle local de uso da API.
