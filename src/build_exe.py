import subprocess

print("Building executable...")

subprocess.run([
    "pyinstaller",
    "--onefile",
    "--name",
    "soccer_simulator",
    "src/app.py"
])

print("Build complete. Check the dist folder.")