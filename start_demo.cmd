@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please follow README.md to install the Python environment first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import sys; assert sys.version_info >= (3, 10)" >nul 2>&1
if errorlevel 1 (
  echo The virtual environment's Python is unavailable or outdated.
  echo Repair it using an installed Python 3.10 or newer:
  echo   py -m venv --upgrade .venv
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  echo See README.md for setup instructions.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import PySide6.QtWidgets, networkx" >nul 2>&1
if errorlevel 1 (
  echo Game dependencies could not be loaded. Run:
  echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
  pause
  exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
