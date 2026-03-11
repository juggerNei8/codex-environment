# src/app.py
import customtkinter as ctk
from prediction_model import predict_match

# GUI window
app = ctk.CTk()
app.title("Soccer Simulator")

def simulate():
    team1 = entry1.get()
    team2 = entry2.get()
    try:
        result = predict_match(team1, team2)
    except Exception as e:
        result = f"Error: {e}"
    result_label.configure(text=result)

# Layout
entry1 = ctk.CTkEntry(app)
entry1.pack(pady=5)
entry2 = ctk.CTkEntry(app)
entry2.pack(pady=5)
button = ctk.CTkButton(app, text="Simulate", command=simulate)
button.pack(pady=10)
result_label = ctk.CTkLabel(app, text="")
result_label.pack(pady=10)

app.mainloop()