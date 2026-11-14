@echo off
chcp 65001 >nul
setlocal EnableExtensions
title Consultor Electoral Espana

REM ============================================================
REM  Lanzador de un clic - Consultor Electoral Espana
REM  Activa .venv, actualiza datos si faltan y abre Streamlit
REM ============================================================

set "PROYECTO=%~dp0"
cd /d "%PROYECTO%"

echo ==========================================
echo   Consultor Electoral Espana - Iniciando
echo ==========================================

REM --- 1) Entorno virtual ---
if not exist "%PROYECTO%.venv\Scripts\python.exe" (
    echo [1/4] Creando entorno virtual...
    python -m venv "%PROYECTO%.venv" || goto :error
) else (
    echo [1/4] Entorno virtual encontrado.
)

set "PY=%PROYECTO%.venv\Scripts\python.exe"
set "ST=%PROYECTO%.venv\Scripts\streamlit.exe"

REM --- 2) Dependencias basicas ---
if not exist "%PROYECTO%.venv\Scripts\streamlit.exe" (
    echo [2/4] Instalando dependencias...
    "%PY%" -m pip install --upgrade pip -q
    "%PY%" -m pip install -r "%PROYECTO%requirements.txt" -q || goto :error
) else (
    echo [2/4] Dependencias OK.
)

REM --- 3) Datos recientes (<= 2 dias) ---
set "NEED_DATA=0"
if not exist "%PROYECTO%data\encuestas_limpias.json" set "NEED_DATA=1"
if exist "%PROYECTO%data\encuestas_limpias.json" (
    "%PY%" -c "import time,os,sys; p=r'%PROYECTO%data\encuestas_limpias.json'; sys.exit(0 if time.time()-os.path.getmtime(p) < 172800 else 1)" || set "NEED_DATA=1"
)

if "%NEED_DATA%"=="1" (
    echo [3/4] Actualizando datos (scraper + IA)...
    "%PY%" "%PROYECTO%scraper.py"
    if exist "%PROYECTO%.env" (
        "%PY%" "%PROYECTO%analizador_ia.py"
    ) else (
        echo       AVISO: sin .env - se omite el informe IA.
    )
) else (
    echo [3/4] Datos recientes presentes.
)

REM --- 4) Servidor + navegador ---
echo [4/4] Arrancando Streamlit en http://localhost:8501
start "" "http://localhost:8501"
"%ST%" run "%PROYECTO%app.py" --server.headless true --server.port 8501

exit /b 0

:error
echo.
echo ERROR: no se pudo iniciar el proyecto. Revisa los mensajes anteriores.
pause
exit /b 1
