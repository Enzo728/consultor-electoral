@echo off
setlocal EnableExtensions
title Consultor Electoral Espana
chcp 65001 >nul 2>nul

set "PROYECTO=%~dp0"
cd /d "%PROYECTO%" || goto :fail

echo ==========================================
echo   Consultor Electoral Espana
echo ==========================================
echo Ruta: %PROYECTO%

if not exist "%PROYECTO%.venv\Scripts\python.exe" (
  echo [1/4] Creando entorno virtual...
  python -m venv "%PROYECTO%.venv"
  if errorlevel 1 goto :fail
) else (
  echo [1/4] Entorno virtual OK
)

set "PY=%PROYECTO%.venv\Scripts\python.exe"
set "ST=%PROYECTO%.venv\Scripts\streamlit.exe"

if not exist "%ST%" (
  echo [2/4] Instalando dependencias...
  "%PY%" -m pip install --upgrade pip -q
  "%PY%" -m pip install -r "%PROYECTO%requirements.txt" -q
  if errorlevel 1 goto :fail
) else (
  echo [2/4] Dependencias OK
)

set "NEED_DATA=0"
if not exist "%PROYECTO%data\encuestas_limpias.json" set "NEED_DATA=1"
if exist "%PROYECTO%data\encuestas_limpias.json" (
  "%PY%" -c "import time,os,sys;p=r'%PROYECTO%data\encuestas_limpias.json';sys.exit(0 if time.time()-os.path.getmtime(p)<172800 else 1)"
  if errorlevel 1 set "NEED_DATA=1"
)

if "%NEED_DATA%"=="1" (
  echo [3/4] Actualizando datos...
  "%PY%" "%PROYECTO%scraper.py"
  if exist "%PROYECTO%.env" "%PY%" "%PROYECTO%analizador_ia.py"
  "%PY%" "%PROYECTO%tracker_historico.py"
) else (
  echo [3/4] Datos recientes. Actualizando historico...
  "%PY%" "%PROYECTO%tracker_historico.py"
)
if errorlevel 1 (
  echo AVISO: tracker devolvio error, se continua igualmente.
)

echo [4/4] Abriendo http://localhost:8501
start "" "http://localhost:8501"
"%ST%" run "%PROYECTO%app.py" --server.headless true --server.port 8501
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo ERROR: fallo al iniciar. Copia este mensaje si persiste.
pause
exit /b 1
