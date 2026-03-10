# One-click PowerShell build with report auto-open

Write-Host "Creating virtual environment if needed..."
python -m venv .venv

Write-Host "Activating virtual environment..."
.\.venv\Scripts\Activate.ps1

Write-Host "Installing requirements..."
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Building executable..."
python src/build_exe.py

Write-Host "Build finished. Running executable..."
Start-Process ".\dist\soccer_simulator.exe"

Write-Host "Done."
Pause