import customtkinter as ctk
import pandas as pd
from prediction_model import predict_match
from commentary_engine import generate_commentary
from animation_engine import animate
from live_data import get_live_scores

ctk.set_appearance_mode("dark")

teams = pd.read_csv("database/teams.csv")["team"].tolist()

app = ctk.CTk()
app.geometry("1000x650")
app.title("AI Football Analytics Simulator")

frame = ctk.CTkFrame(app)
frame.pack(pady=20)

team1 = ctk.CTkComboBox(frame,values=teams)
team1.set(teams[0])
team1.grid(row=0,column=0,padx=20)

team2 = ctk.CTkComboBox(frame,values=teams)
team2.set(teams[1])
team2.grid(row=0,column=1,padx=20)

canvas = ctk.CTkCanvas(app,width=800,height=400,bg="green")
canvas.pack(pady=20)

def simulate():

    s1,s2,p1,p2 = predict_match(team1.get(),team2.get())

    animate(canvas)

    result.configure(text=f"{team1.get()} {s1} - {s2} {team2.get()}")
    prob.configure(text=f"Win Probabilities: {p1}% vs {p2}%")

    commentary.configure(text=generate_commentary())

simulate_btn = ctk.CTkButton(app,text="Simulate Match",command=simulate)
simulate_btn.pack()

live_btn = ctk.CTkButton(app,text="Get Live Data",command=lambda:live.configure(text=get_live_scores()))
live_btn.pack(pady=10)

result = ctk.CTkLabel(app,text="",font=("Arial",28))
result.pack()

prob = ctk.CTkLabel(app,text="")
prob.pack()

commentary = ctk.CTkLabel(app,text="")
commentary.pack()

live = ctk.CTkLabel(app,text="")
live.pack()

app.mainloop()