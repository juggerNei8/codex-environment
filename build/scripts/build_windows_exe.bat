@echo off
REM One-click Windows build with report auto-open

echo Creating virtual environment if needed...
python -m venv .venv

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing requirements...
pip install --upgrade pip
pip install -r requirements.txt

echo Building executable...
python src/build_exe.py

echo Build finished. Running executable...
.\dist\soccer_simulator.exe

pause