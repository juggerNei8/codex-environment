import random
import math


class AnimationEngine:
    def __init__(
        self,
        canvas,
        commentary_callback=None,
        goal_callback=None,
        possession_callback=None,
        stats_callback=None,
        timeline_callback=None
    ):
        self.canvas = canvas
        self.commentary_callback = commentary_callback
        self.goal_callback = goal_callback
        self.possession_callback = possession_callback
        self.stats_callback = stats_callback
        self.timeline_callback = timeline_callback

        self.pitch_w = 900
        self.pitch_h = 500
        self.running = False
        self.frame_ms = 70

        self.home_team_name = "HOME"
        self.away_team_name = "AWAY"
        self.home_formation = "4-3-3"
        self.away_formation = "4-2-3-1"

        self.players = []
        self.ball = None
        self.line_items = []

        self.ball_x = 450.0
        self.ball_y = 250.0
        self.ball_dx = 0.0
        self.ball_dy = 0.0

        self.home_score = 0
        self.away_score = 0
        self.home_pos_ticks = 1
        self.away_pos_ticks = 1

        self.stats = {
            "home_shots": 0,
            "away_shots": 0,
            "home_on_target": 0,
            "away_on_target": 0,
            "home_passes": 0,
            "away_passes": 0,
            "home_saves": 0,
            "away_saves": 0
        }

        self.home_tactic = {"press": 0.58, "pass_speed": 1.0, "shot_bias": 0.11, "shape": "balanced"}
        self.away_tactic = {"press": 0.58, "pass_speed": 1.0, "shot_bias": 0.11, "shape": "balanced"}

        self.tick_count = 0

        self.draw_pitch()
        self.create_players()
        self.create_ball()
        self.push_stats()

    # ------------------------------------------------

    def say(self, text):
        if self.commentary_callback:
            self.commentary_callback(text)

    def timeline(self, minute, kind, text):
        if self.timeline_callback:
            self.timeline_callback(minute, kind, text)

    def configure_match(self, home_team, away_team, home_formation, away_formation):
        self.home_team_name = home_team or "HOME"
        self.away_team_name = away_team or "AWAY"
        self.home_formation = home_formation or "4-3-3"
        self.away_formation = away_formation or "4-2-3-1"
        self.reset_match()

    def set_tactics(self, home_tactic, away_tactic):
        if home_tactic:
            self.home_tactic = home_tactic
        if away_tactic:
            self.away_tactic = away_tactic

    def get_average_stamina(self, team):
        group = [p for p in self.players if p["team"] == team]
        if not group:
            return 100.0
        return sum(p["stamina"] for p in group) / len(group)

    def get_possession_snapshot(self):
        total = self.home_pos_ticks + self.away_pos_ticks
        home = int(self.home_pos_ticks / total * 100)
        away = 100 - home
        return home, away

    def push_possession(self):
        home, away = self.get_possession_snapshot()
        if self.possession_callback:
            self.possession_callback(home, away)

    def push_stats(self):
        if self.stats_callback:
            self.stats_callback(self.stats.copy())

    # ------------------------------------------------
    # PITCH
    # ------------------------------------------------

    def draw_pitch(self):
        self.canvas.delete("all")
        self.line_items = []

        stripe = 60
        for i in range(0, self.pitch_w, stripe):
            color = "#2e7d32" if (i // stripe) % 2 == 0 else "#348f3a"
            self.canvas.create_rectangle(i, 0, i + stripe, self.pitch_h, fill=color, outline="")

        self.canvas.create_line(self.pitch_w / 2, 0, self.pitch_w / 2, self.pitch_h, fill="white", width=2)
        self.canvas.create_oval(390, 190, 510, 310, outline="white", width=2)

        self.canvas.create_rectangle(0, 140, 120, 360, outline="white", width=2)
        self.canvas.create_rectangle(780, 140, 900, 360, outline="white", width=2)

        self.canvas.create_rectangle(0, 190, 50, 310, outline="white", width=2)
        self.canvas.create_rectangle(850, 190, 900, 310, outline="white", width=2)

        self.canvas.create_rectangle(0, 210, 10, 290, fill="white", outline="white")
        self.canvas.create_rectangle(890, 210, 900, 290, fill="white", outline="white")

        # pitch badges / fallback
        self.canvas.create_text(70, 24, text=self.home_team_name[:10], fill="white", font=("Arial", 10, "bold"))
        self.canvas.create_text(830, 24, text=self.away_team_name[:10], fill="white", font=("Arial", 10, "bold"))

    # ------------------------------------------------

    def get_positions(self, formation, side):
        if side == "home":
            if formation == "4-2-3-1":
                return [
                    ("GK", 70, 250),
                    ("LB", 180, 90), ("CB", 180, 195), ("CB", 180, 305), ("RB", 180, 410),
                    ("CDM", 300, 180), ("CDM", 300, 320),
                    ("LW", 430, 110), ("CAM", 430, 250), ("RW", 430, 390),
                    ("ST", 560, 250)
                ]
            return [
                ("GK", 70, 250),
                ("LB", 180, 90), ("CB", 180, 195), ("CB", 180, 305), ("RB", 180, 410),
                ("CM", 320, 140), ("CM", 320, 250), ("CM", 320, 360),
                ("LW", 500, 120), ("ST", 560, 250), ("RW", 500, 380)
            ]

        if formation == "4-2-3-1":
            return [
                ("GK", 830, 250),
                ("LB", 720, 90), ("CB", 720, 195), ("CB", 720, 305), ("RB", 720, 410),
                ("CDM", 600, 180), ("CDM", 600, 320),
                ("LW", 470, 110), ("CAM", 470, 250), ("RW", 470, 390),
                ("ST", 340, 250)
            ]
        return [
            ("GK", 830, 250),
            ("LB", 720, 90), ("CB", 720, 195), ("CB", 720, 305), ("RB", 720, 410),
            ("CM", 580, 140), ("CM", 580, 250), ("CM", 580, 360),
            ("LW", 400, 120), ("ST", 340, 250), ("RW", 400, 380)
        ]

    def create_players(self):
        self.players = []

        home_positions = self.get_positions(self.home_formation, "home")
        away_positions = self.get_positions(self.away_formation, "away")

        for idx, (role, x, y) in enumerate(home_positions, start=1):
            obj = self.canvas.create_oval(x, y, x + 16, y + 16, fill="#ef4444", outline="")
            label = self.canvas.create_text(x + 8, y - 10, text=role, fill="white", font=("Arial", 8, "bold"))
            self.players.append({
                "team": "home",
                "role": role,
                "x": float(x),
                "y": float(y),
                "home_x": float(x),
                "home_y": float(y),
                "obj": obj,
                "label": label,
                "stamina": 100.0,
                "name": f"H{idx}"
            })

        for idx, (role, x, y) in enumerate(away_positions, start=1):
            obj = self.canvas.create_oval(x, y, x + 16, y + 16, fill="#3b82f6", outline="")
            label = self.canvas.create_text(x + 8, y - 10, text=role, fill="white", font=("Arial", 8, "bold"))
            self.players.append({
                "team": "away",
                "role": role,
                "x": float(x),
                "y": float(y),
                "home_x": float(x),
                "home_y": float(y),
                "obj": obj,
                "label": label,
                "stamina": 100.0,
                "name": f"A{idx}"
            })

    def create_ball(self):
        self.ball = self.canvas.create_oval(self.ball_x, self.ball_y, self.ball_x + 10, self.ball_y + 10, fill="white", outline="black")

    # ------------------------------------------------

    def center_of(self, player):
        return player["x"] + 8, player["y"] + 8

    def find_nearest_player(self):
        best = None
        best_d = 10**9
        for p in self.players:
            px, py = self.center_of(p)
            d = math.hypot(px - self.ball_x, py - self.ball_y)
            if d < best_d:
                best_d = d
                best = p
        return best, best_d

    def teammates(self, team):
        return [p for p in self.players if p["team"] == team]

    def goalkeeper_for(self, team):
        for p in self.players:
            if p["team"] == team and p["role"] == "GK":
                return p
        return None

    # ------------------------------------------------
    # MOVEMENT
    # ------------------------------------------------

    def move_players(self):
        nearest, _ = self.find_nearest_player()

        for p in self.players:
            px, py = self.center_of(p)
            target_x = p["home_x"]
            target_y = p["home_y"]

            if nearest is not None and p is nearest:
                target_x = self.ball_x
                target_y = self.ball_y

            tactic = self.home_tactic if p["team"] == "home" else self.away_tactic

            if p["team"] == "home" and p["role"] in ("ST", "LW", "RW", "CAM") and tactic["shape"] == "attack":
                target_x = min(800, target_x + 35)

            if p["team"] == "away" and p["role"] in ("ST", "LW", "RW", "CAM") and tactic["shape"] == "attack":
                target_x = max(100, target_x - 35)

            dx = (target_x - px) * 0.03
            dy = (target_y - py) * 0.03

            pace = max(0.45, p["stamina"] / 100.0)
            dx *= pace
            dy *= pace

            p["x"] += dx
            p["y"] += dy

            self.canvas.move(p["obj"], dx, dy)
            self.canvas.move(p["label"], dx, dy)

            p["stamina"] = max(35.0, p["stamina"] - 0.012)

    # ------------------------------------------------
    # PASSING / TRACKER LINES / SHOTS
    # ------------------------------------------------

    def clear_tracker_lines(self):
        for item in self.line_items:
            try:
                self.canvas.delete(item)
            except Exception:
                pass
        self.line_items = []

    def draw_tracker_line(self, x1, y1, x2, y2, color):
        item = self.canvas.create_line(x1, y1, x2, y2, fill=color, width=2, dash=(4, 2))
        self.line_items.append(item)

    def kick_ball_toward(self, tx, ty, power):
        dx = tx - self.ball_x
        dy = ty - self.ball_y
        dist = math.hypot(dx, dy) + 0.0001
        self.ball_dx = (dx / dist) * power
        self.ball_dy = (dy / dist) * power

    def pass_ball(self, team):
        mates = self.teammates(team)
        if not mates:
            return

        if team == "home":
            mates = sorted(mates, key=lambda p: p["x"], reverse=True)
            speed = self.home_tactic["pass_speed"]
            color = "#ffb4b4"
        else:
            mates = sorted(mates, key=lambda p: p["x"])
            speed = self.away_tactic["pass_speed"]
            color = "#b9d7ff"

        target = random.choice(mates[:4] if len(mates) >= 4 else mates)
        tx, ty = self.center_of(target)

        self.draw_tracker_line(self.ball_x, self.ball_y, tx, ty, color)
        self.kick_ball_toward(tx, ty, power=random.uniform(4.0, 6.4) * speed)

        if team == "home":
            self.home_pos_ticks += 1
            self.stats["home_passes"] += 1
        else:
            self.away_pos_ticks += 1
            self.stats["away_passes"] += 1

    def attempt_shot(self, team):
        if team == "home":
            goal_x = 895
            goal_y = random.randint(220, 280)
            self.stats["home_shots"] += 1
            self.stats["home_on_target"] += 1
            color = "#ffcccb"
        else:
            goal_x = 5
            goal_y = random.randint(220, 280)
            self.stats["away_shots"] += 1
            self.stats["away_on_target"] += 1
            color = "#cbe1ff"

        self.draw_tracker_line(self.ball_x, self.ball_y, goal_x, goal_y, color)
        self.kick_ball_toward(goal_x, goal_y, power=random.uniform(8.0, 11.5))
        self.say("Shot taken!")

    def maybe_action(self):
        nearest, dist = self.find_nearest_player()

        if nearest is None or dist > 36:
            return

        team = nearest["team"]
        role = nearest["role"]

        if team == "home":
            self.home_pos_ticks += 1
            tactic = self.home_tactic
            close_to_goal = self.ball_x > 700
        else:
            self.away_pos_ticks += 1
            tactic = self.away_tactic
            close_to_goal = self.ball_x < 200

        shot_bias = tactic["shot_bias"]

        if role in ("ST", "LW", "RW", "CAM") and close_to_goal and random.random() < shot_bias:
            self.attempt_shot(team)
        else:
            self.pass_ball(team)

        # occasional timeline events
        minute = min(99, max(1, self.tick_count // 14))
        if random.random() < 0.03:
            self.timeline(minute, "card", "Yellow card shown for a late challenge.")
        if random.random() < 0.02:
            self.timeline(minute, "substitution", "Tactical substitution made.")

    def move_ball(self):
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy

        self.ball_dx *= 0.965
        self.ball_dy *= 0.965

        self.canvas.coords(self.ball, self.ball_x, self.ball_y, self.ball_x + 10, self.ball_y + 10)

    # ------------------------------------------------
    # GK / GOALS
    # ------------------------------------------------

    def goalkeeper_dive(self, keeper, direction):
        dive = 16 if direction == "right" else -16
        self.canvas.move(keeper["obj"], dive, 0)
        self.canvas.move(keeper["label"], dive, 0)
        keeper["x"] += dive

    def maybe_goalkeeper_save(self):
        left_gk = self.goalkeeper_for("home")
        right_gk = self.goalkeeper_for("away")

        if self.ball_x < 80 and 180 < self.ball_y < 320 and left_gk:
            self.goalkeeper_dive(left_gk, "left")
            if random.random() < 0.65:
                self.ball_dx = abs(self.ball_dx) * 0.55
                self.ball_dy *= 0.45
                self.stats["home_saves"] += 1
                self.say("Great save by the home keeper!")
                return True

        if self.ball_x > 820 and 180 < self.ball_y < 320 and right_gk:
            self.goalkeeper_dive(right_gk, "right")
            if random.random() < 0.65:
                self.ball_dx = -abs(self.ball_dx) * 0.55
                self.ball_dy *= 0.45
                self.stats["away_saves"] += 1
                self.say("Brilliant save by the away keeper!")
                return True

        return False

    def check_goal(self):
        if self.ball_x <= 3 and 210 <= self.ball_y <= 290:
            self.away_score += 1
            if self.goal_callback:
                self.goal_callback("away")
            self.reset_after_goal()

        if self.ball_x >= 897 and 210 <= self.ball_y <= 290:
            self.home_score += 1
            if self.goal_callback:
                self.goal_callback("home")
            self.reset_after_goal()

    def reset_after_goal(self):
        self.ball_x = 450
        self.ball_y = 250
        self.ball_dx = 0.0
        self.ball_dy = 0.0
        self.canvas.coords(self.ball, 445, 245, 455, 255)

    # ------------------------------------------------

    def animate(self):
        if not self.running:
            return

        try:
            self.tick_count += 1

            if self.tick_count % 10 == 0:
                self.clear_tracker_lines()

            self.move_players()

            if random.random() < 0.18:
                self.maybe_action()

            self.move_ball()
            self.maybe_goalkeeper_save()
            self.check_goal()

            if self.tick_count % 12 == 0:
                self.push_possession()
                self.push_stats()

        except Exception as e:
            print("Animation error:", e)

        self.canvas.after(self.frame_ms, self.animate)

    def reset_match(self):
        self.running = False
        self.home_score = 0
        self.away_score = 0
        self.home_pos_ticks = 1
        self.away_pos_ticks = 1
        self.stats = {
            "home_shots": 0,
            "away_shots": 0,
            "home_on_target": 0,
            "away_on_target": 0,
            "home_passes": 0,
            "away_passes": 0,
            "home_saves": 0,
            "away_saves": 0
        }
        self.ball_x = 450.0
        self.ball_y = 250.0
        self.ball_dx = 0.0
        self.ball_dy = 0.0
        self.tick_count = 0

        self.draw_pitch()
        self.create_players()
        self.create_ball()
        self.push_possession()
        self.push_stats()