@echo off
echo ===================================================
echo   Iniciando Portal de Soporte IA - DP-800
echo ===================================================

echo.
echo [1/3] Comprobando e instalando modelos de IA (Ollama)...
ollama pull nomic-embed-text
ollama pull llama3.2

echo.
echo [2/3] Configurando el entorno virtual de Python...
IF NOT EXIST "venv" (
    echo Creando nuevo entorno virtual...
    python -m venv venv
)
call venv\Scripts\activate
echo Instalando dependencias...
pip install -r requirements.txt > nul

echo.
echo [3/3] Lanzando la API y abriendo el navegador...
start http://localhost:8000
python -m uvicorn app.main:app --reload

pause