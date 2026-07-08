@echo off
echo Ativando ambiente virtual...
call venv\Scripts\activate.bat
echo.
echo ✅ Ambiente virtual ativado!
echo Digite 'pip install -r requirements.txt' para instalar as dependências
echo Digite 'python main.py' para executar o projeto
cmd /k
