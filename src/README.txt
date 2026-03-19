BACKGROUND FIX PACK

What to update
- app.py

Where to place it
- C:\Project X\codex-environment-main\src\app.py

How to apply
- Open app_background_patch.txt
- Replace the listed methods/import in app.py
- Install Pillow if needed:
  cd /d "C:\Project X\codex-environment-main\src"
  pip install pillow

How to run
- cd /d "C:\Project X\codex-environment-main\src"
- python run_simulator.py

Why it matters
- Tkinter PhotoImage is limited and can reject valid-looking PNG files
- Pillow improves image decoding and resizing reliability
- This patch makes your background banners much more stable
