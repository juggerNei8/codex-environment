# src/utils.py
import os
import sys

def resource_path(relative_path: str) -> str:
    # PyInstaller temp folder
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        # go **one level up from src/** to project root
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    
    full_path = os.path.normpath(os.path.join(base_path, relative_path))
    # DEBUG: print paths
    print(f"[DEBUG] resource_path({relative_path}) -> {full_path}")
    return full_path