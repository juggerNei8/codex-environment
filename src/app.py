import customtkinter as ctk
import random
import os
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

teams = [
    "Arsenal",
    "Barcelona",
    "Real Madrid",
    "Manchester City",
    "Bayern Munich",
    "Juventus",
    "PSG",
    "Liverpool"
]

def simulate_match():
    team1 = team1_select.get()
    team2 = team2_select.get()

    if team1 == team2:
        result_label.configure(text="Select two different teams.")
        return

    score1 = random.randint(0, 5)
    score2 = random.randint(0, 5)

    possession1 = random.randint(40, 60)
    possession2 = 100 - possession1

    shots1 = random.randint(5, 15)
    shots2 = random.randint(5, 15)

    result = f"{team1} {score1} - {score2} {team2}"

    stats = (
        f"\nPossession: {team1} {possession1}% | {team2} {possession2}%\n"
        f"Shots: {team1} {shots1} | {team2} {shots2}"
    )

    result_label.configure(text=result + stats)

    save_report(team1, team2, score1, score2, possession1, possession2, shots1, shots2)


def save_report(t1, t2, s1, s2, p1, p2, sh1, sh2):

    os.makedirs("reports", exist_ok=True)

    filename = f"reports/match_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    with open(filename, "w") as f:
        f.write("Soccer Simulator Match Report\n\n")
        f.write(f"{t1} {s1} - {s2} {t2}\n\n")
        f.write(f"Possession: {t1} {p1}% | {t2} {p2}%\n")
        f.write(f"Shots: {t1} {sh1} | {t2} {sh2}\n")

    os.system(f'notepad "{filename}"')


app = ctk.CTk()
app.title("AI Soccer Simulator")
app.geometry("900x600")

title = ctk.CTkLabel(app, text="⚽ AI Soccer Simulator", font=("Arial", 32))
title.pack(pady=30)

team_frame = ctk.CTkFrame(app)
team_frame.pack(pady=20)

team1_select = ctk.CTkComboBox(team_frame, values=teams)
team1_select.set(teams[0])
team1_select.grid(row=0, column=0, padx=20, pady=10)

vs_label = ctk.CTkLabel(team_frame, text="VS", font=("Arial", 18))
vs_label.grid(row=0, column=1, padx=10)

team2_select = ctk.CTkComboBox(team_frame, values=teams)
team2_select.set(teams[1])
team2_select.grid(row=0, column=2, padx=20, pady=10)

simulate_button = ctk.CTkButton(
    app,
    text="Simulate Match",
    width=200,
    height=50,
    command=simulate_match
)

simulate_button.pack(pady=20)

result_label = ctk.CTkLabel(app, text="Select teams and simulate a match", font=("Arial", 20))
result_label.pack(pady=30)

app.mainloop()