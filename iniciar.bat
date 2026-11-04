@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Falta instalar Python y las dependencias del proyecto. Consulta README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" run.py
if errorlevel 1 pause
