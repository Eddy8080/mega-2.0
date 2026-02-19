# Sistema Híbrido Mega-Sena

Sistema desktop desenvolvido em Python para análise estatística, simulação e geração de palpites para a Mega-Sena. O projeto utiliza uma arquitetura híbrida que combina estatística clássica, simulações de Monte Carlo e Inteligência Artificial Generativa (Google Gemini).

## Funcionalidades Principais

- **Análise Estatística:** Frequência, atrasos, pares/ímpares, primos, ciclos, temperatura, quadrantes, etc.
- **Simulação:** Método de Monte Carlo para validação de probabilidades e comparação com histórico real.
- **IA Generativa:** Integração com Google Gemini 2.0 Flash para insights, chat híbrido e geração de palpites fundamentados.
- **Visualização:** Gráficos de barras, heatmaps de correlação e gráficos de linha.
- **Gestão de Dados:** Importação automática de dados (CSV/Excel), backup e banco de dados SQLite local.
- **Relatórios:** Geração de relatórios completos em PDF.

## Pré-requisitos

- **Python 3.8** ou superior.
- Conexão com a internet (para download de dados e comunicação com a API Gemini).
- *(Opcional)* Placa de vídeo NVIDIA para aceleração de cálculos via GPU.

## Instalação

1. Baixe os arquivos do projeto para uma pasta local.

2. Abra o terminal na pasta do projeto e instale as dependências obrigatórias:

```bash
pip install numpy pandas matplotlib google-genai openpyxl reportlab
```

### Aceleração por GPU (Opcional)

O sistema suporta aceleração de hardware para simulações pesadas. Se você possui uma GPU NVIDIA, instale o `CuPy` correspondente à versão do seu CUDA (exemplo para CUDA 12.x):

```bash
pip install cupy-cuda12x
```
*(Consulte a documentação do CuPy para a versão exata do seu driver).*

Opcionalmente, para experimentos com JAX:
```bash
pip install jax jaxlib
```

## Configuração da API (Google Gemini)

Para utilizar as funcionalidades de Inteligência Artificial (Chat, Palpites IA, Análises Avançadas), é necessário uma chave de API gratuita do Google.

1. Gere sua chave em: Google AI Studio.
2. Ao executar o programa, clique no botão **"Config. Token"** na parte inferior da interface e cole sua chave.
3. O sistema criará automaticamente um arquivo `config.json` com suas credenciais.

## Como Executar

Certifique-se de estar na pasta do projeto e execute o arquivo principal:

```bash
python main.py
```

## Estrutura do Projeto

- **`main.py`**: Inicializador da aplicação.
- **`interface.py`**: Interface gráfica (GUI) construída com Tkinter.
- **`brain.py`**: Núcleo do sistema (Cálculos, IA, Lógica de Negócio).
- **`database.py`**: Gerenciamento do banco de dados SQLite (`mega_sena.db`).
- **`importar_dados.py`**: Scripts para leitura e tratamento de dados (ETL).
- **`config.json`**: Armazena o token da API e configurações de delay.
- **`quota.json`**: Controla o limite diário de requisições à IA para evitar bloqueios.

## Notas

- O sistema cria backups automáticos do banco de dados na pasta `backups/`.
- Caso não possua o arquivo `mega_sena.xlsx`, o sistema tentará baixar a base de dados mais recente de um repositório público.