import PyInstaller.__main__

PyInstaller.__main__.run([
    "src/app.py",
    "--onefile",
    "--windowed",
    "--name=soccer_simulator"
])