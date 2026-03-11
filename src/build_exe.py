# src/build_exe.py
import PyInstaller.__main__

PyInstaller.__main__.run([
    '--name=soccer_simulator',
    '--onefile',
    '--windowed',
    '--add-data=../database;database',
    '--add-data=../assets;assets',
    'app.py'
])