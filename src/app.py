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
import tkinter as tk
from match_engine import simulate_match

def play_match():

    team1 = team1_entry.get()
    team2 = team2_entry.get()

    result = simulate_match(team1, team2)

    output.delete("1.0", tk.END)

    output.insert(tk.END, result["score"] + "\n")
    output.insert(tk.END, f"Possession: {result['possession']}\n")
    output.insert(tk.END, f"Shots: {result['shots']}\n")
    output.insert(tk.END, f"xG: {result['xg']}\n\n")

    for line in result["timeline"]:
        output.insert(tk.END, line + "\n")


root = tk.Tk()
root.title("Football Match Simulator")

team1_entry = tk.Entry(root)
team2_entry = tk.Entry(root)

team1_entry.pack()
team2_entry.pack()

play_button = tk.Button(root, text="Simulate Match", command=play_match)
play_button.pack()

output = tk.Text(root, height=20)
output.pack()

root.mainloop()
from match_engine import run_match
def simulate():

    team1 = team1_entry.get()
    team2 = team2_entry.get()

    id1 = find_team_id(team1)
    id2 = find_team_id(team2)

    if id1 is None or id2 is None:
        result_label.config(text="Team not found in database")
        return

    result = run_match(id1, id2)

    result_label.config(text=f"{result['score'][0]} - {result['score'][1]}")
from pitch_view import PitchView
from animation_engine import AnimationEngine
pitch = PitchView(app)

anim = AnimationEngine(pitch.canvas)
anim.animate()