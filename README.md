# 🚀 Automação Azure Board - BDD Generator

Automação inteligente que monitora Azure DevOps e gera testes BDD em Gherkin.

## 📋 Pré-requisitos

- Python 3.10+
- Git

## ⚙️ Instalação

### 1. Clone o repositório
```bash
git clone <seu-repo>
cd automacao-azure-board
```

### 2. Crie um ambiente virtual
```bash
# Windows (CMD)
python -m venv venv
venv\Scripts\activate.bat

# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as credenciais
Crie um arquivo `.env` baseado em `.env.example`:
```bash
cp .env.example .env
```

Preencha com suas credenciais:
```
AZURE_ORGANIZATION=seu_org
AZURE_PROJECT=seu_project
AZURE_PAT=seu_pat
GEMINI_API_KEY=sua_api_key
GEMINI_MODEL=gemini-2.5-flash
```

## 🚀 Execução

```bash
# Certifique-se que o venv está ativado
python main.py
```

## 📁 Estrutura do Projeto

```
automacao-azure-board/
├── main.py                      # Ponto de entrada
├── requirements.txt             # Dependências
├── .env.example                 # Template de variáveis
├── ativar_venv.bat             # Script para ativar venv (Windows)
├── config/
│   └── settings.py             # Configurações
├── services/
│   ├── azure_service.py        # API Azure DevOps
│   ├── gemini_service.py       # API Gemini
│   └── file_service.py         # Gerenciamento de arquivos
├── data/
│   └── historias_processadas.json  # Histórico de processamento
└── features/
    └── *.feature               # Arquivos gerados em Gherkin
```

## 🔐 Segurança

⚠️ **Nunca commite o arquivo `.env` com credenciais reais!**

O arquivo `.gitignore` está configurado para:
- Ignorar `.env`
- Ignorar a pasta `venv/`
- Ignorar `__pycache__/`
- Ignorar logs

## 📝 Notas

- O histórico de histórias processadas é mantido em `data/historias_processadas.json`
- Novos arquivos `.feature` são salvos em `features/`
- O projeto monitora a coluna "Aguardando Dev" no Azure DevOps

## 🤝 Contribuindo

1. Ative o venv
2. Instale as dependências
3. Faça suas alterações
4. Execute testes (quando disponíveis)
5. Faça commit e push

## ⚡ Atalho Rápido (Windows)

Execute o script:
```bash
ativar_venv.bat
```

Isso abrirá um terminal com o venv já ativado!
