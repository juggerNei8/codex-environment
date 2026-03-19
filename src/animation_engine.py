import math
import random

from asset_manager import AssetManager


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

        self.assets = AssetManager()

        self.pitch_w = 900
        self.pitch_h = 500
        self.running = False
        self.frame_ms = 16

        self.home_team_name = "HOME"
        self.away_team_name = "AWAY"
        self.home_formation = "4-3-3"
        self.away_formation = "4-2-3-1"

        self.home_tactic = {"press": 0.58, "pass_speed": 1.0, "shot_bias": 0.18, "shape": "balanced"}
        self.away_tactic = {"press": 0.58, "pass_speed": 1.0, "shot_bias": 0.18, "shape": "balanced"}

        self.players = []
        self.ball = None
        self.ball_img = None
        self.pitch_img = None
        self.pitch_bg = None

        self.line_items = []
        self.badge_items = []

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

        self.tick_count = 0
        self.last_shot_tick = -999
        self.last_goal_tick = -999

        self.draw_pitch()
        self.create_players()
        self.create_ball()
        self.push_stats()
        self.push_possession()

    # ------------------------------------------------

    def say(self, text):
        if self.commentary_callback:
            self.commentary_callback(text)

    def timeline(self, minute, kind, text):
        if self.timeline_callback:
            self.timeline_callback(minute, kind, text)

    def set_tactics(self, home_tactic, away_tactic):
        if home_tactic:
            self.home_tactic = home_tactic
        if away_tactic:
            self.away_tactic = away_tactic

    def configure_match(self, home_team, away_team, home_formation, away_formation):
        self.home_team_name = home_team or "HOME"
        self.away_team_name = away_team or "AWAY"
        self.home_formation = home_formation or "4-3-3"
        self.away_formation = away_formation or "4-2-3-1"
        self.reset_match()

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
        if self.possession_callback:
            home, away = self.get_possession_snapshot()
            self.possession_callback(home, away)

    def push_stats(self):
        if self.stats_callback:
            self.stats_callback(self.stats.copy())

    # ------------------------------------------------
    # PITCH / BADGES
    # ------------------------------------------------

    def draw_pitch(self):
        self.canvas.delete("all")
        self.line_items = []
        self.badge_items = []

        pitch_image = self.assets.load_pitch_image()
        if pitch_image is not None:
            self.pitch_img = pitch_image
            self.pitch_bg = self.canvas.create_image(450, 250, image=self.pitch_img)
        else:
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

        self.badge_items.append(
            self.canvas.create_text(75, 24, text=self.home_team_name[:14], fill="white", font=("Arial", 11, "bold"))
        )
        self.badge_items.append(
            self.canvas.create_text(825, 24, text=self.away_team_name[:14], fill="white", font=("Arial", 11, "bold"))
        )

    # ------------------------------------------------
    # FORMATIONS
    # ------------------------------------------------

    def get_positions(self, formation, side):
        formations = {
            "4-3-3": [
                ("GK", 70, 250),
                ("LB", 180, 90), ("CB", 180, 195), ("CB", 180, 305), ("RB", 180, 410),
                ("CM", 320, 140), ("CM", 320, 250), ("CM", 320, 360),
                ("LW", 500, 120), ("ST", 560, 250), ("RW", 500, 380),
            ],
            "4-2-3-1": [
                ("GK", 70, 250),
                ("LB", 180, 90), ("CB", 180, 195), ("CB", 180, 305), ("RB", 180, 410),
                ("CDM", 300, 180), ("CDM", 300, 320),
                ("LW", 430, 110), ("CAM", 430, 250), ("RW", 430, 390),
                ("ST", 560, 250),
            ],
            "3-5-2": [
                ("GK", 70, 250),
                ("CB", 180, 130), ("CB", 180, 250), ("CB", 180, 370),
                ("LM", 290, 90), ("CM", 320, 180), ("CM", 320, 250), ("CM", 320, 320), ("RM", 290, 410),
                ("ST", 520, 200), ("ST", 520, 300),
            ],
            "4-4-2": [
                ("GK", 70, 250),
                ("LB", 180, 90), ("CB", 180, 195), ("CB", 180, 305), ("RB", 180, 410),
                ("LM", 330, 90), ("CM", 320, 210), ("CM", 320, 290), ("RM", 330, 410),
                ("ST", 520, 200), ("ST", 520, 300),
            ],
        }

        base = formations.get(formation, formations["4-3-3"])

        if side == "home":
            return base

        return [(role, self.pitch_w - x, y) for role, x, y in base]

    # ------------------------------------------------

    def create_players(self):
        self.players = []

        home_positions = self.get_positions(self.home_formation, "home")
        away_positions = self.get_positions(self.away_formation, "away")

        for idx, (role, x, y) in enumerate(home_positions, start=1):
            name = f"{self.home_team_name[:3].upper()}-{idx}"
            obj = self.canvas.create_oval(x, y, x + 18, y + 18, fill="#ef4444", outline="")
            label = self.canvas.create_text(x + 9, y - 12, text=name, fill="white", font=("Arial", 7, "bold"))
            role_label = self.canvas.create_text(x + 9, y - 25, text=role, fill="#e2e8f0", font=("Arial", 7))
            self.players.append({
                "team": "home",
                "role": role,
                "x": float(x),
                "y": float(y),
                "home_x": float(x),
                "home_y": float(y),
                "obj": obj,
                "label": label,
                "role_label": role_label,
                "stamina": 100.0,
                "name": name
            })

        for idx, (role, x, y) in enumerate(away_positions, start=1):
            name = f"{self.away_team_name[:3].upper()}-{idx}"
            obj = self.canvas.create_oval(x, y, x + 18, y + 18, fill="#3b82f6", outline="")
            label = self.canvas.create_text(x + 9, y - 12, text=name, fill="white", font=("Arial", 7, "bold"))
            role_label = self.canvas.create_text(x + 9, y - 25, text=role, fill="#e2e8f0", font=("Arial", 7))
            self.players.append({
                "team": "away",
                "role": role,
                "x": float(x),
                "y": float(y),
                "home_x": float(x),
                "home_y": float(y),
                "obj": obj,
                "label": label,
                "role_label": role_label,
                "stamina": 100.0,
                "name": name
            })

    def create_ball(self):
        ball_img = self.assets.load_ball_image()
        if ball_img is not None:
            self.ball_img = ball_img
            self.ball = self.canvas.create_image(self.ball_x, self.ball_y, image=self.ball_img)
        else:
            self.ball = self.canvas.create_oval(
                self.ball_x, self.ball_y, self.ball_x + 10, self.ball_y + 10,
                fill="white", outline="black"
            )

    # ------------------------------------------------

    def center_of(self, player):
        return player["x"] + 9, player["y"] + 9

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
    # TRACKER LINES
    # ------------------------------------------------

    def clear_tracker_lines(self):
        for item in self.line_items:
            try:
                self.canvas.delete(item)
            except Exception:
                pass
        self.line_items = []

    def draw_tracker_line(self, x1, y1, x2, y2, color, width=3):
        item = self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width, dash=(6, 3))
        self.line_items.append(item)

    # ------------------------------------------------
    # MOVEMENT / PASSING / SHOTS
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

            if p["team"] == "home" and p["role"] in ("ST", "LW", "RW", "CAM", "LM", "RM") and tactic["shape"] == "attack":
                target_x = min(820, target_x + 40)

            if p["team"] == "away" and p["role"] in ("ST", "LW", "RW", "CAM", "LM", "RM") and tactic["shape"] == "attack":
                target_x = max(80, target_x - 40)

            dx = (target_x - px) * 0.055
            dy = (target_y - py) * 0.055

            pace = max(0.55, p["stamina"] / 100.0)
            dx *= pace
            dy *= pace

            p["x"] += dx
            p["y"] += dy

            self.canvas.move(p["obj"], dx, dy)
            self.canvas.move(p["label"], dx, dy)
            self.canvas.move(p["role_label"], dx, dy)

            p["stamina"] = max(35.0, p["stamina"] - 0.02)

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
            color = "#ffd1d1"
        else:
            mates = sorted(mates, key=lambda p: p["x"])
            speed = self.away_tactic["pass_speed"]
            color = "#cfe3ff"

        pool = mates[:6] if len(mates) >= 6 else mates
        target = random.choice(pool)
        tx, ty = self.center_of(target)

        self.draw_tracker_line(self.ball_x, self.ball_y, tx, ty, color, width=3)
        self.kick_ball_toward(tx, ty, power=random.uniform(5.5, 8.0) * speed)

        if team == "home":
            self.home_pos_ticks += 1
            self.stats["home_passes"] += 1
        else:
            self.away_pos_ticks += 1
            self.stats["away_passes"] += 1

    def _shot_success_probability(self, team, role):
        tactic = self.home_tactic if team == "home" else self.away_tactic
        bias = max(0.16, float(tactic.get("shot_bias", 0.18)))

        role_bonus = {
            "ST": 0.18,
            "CAM": 0.10,
            "LW": 0.08,
            "RW": 0.08,
            "LM": 0.05,
            "RM": 0.05,
            "CM": 0.03,
        }.get(role, 0.0)

        distance_factor = 0.0
        if team == "home":
            if self.ball_x > 760:
                distance_factor += 0.16
            elif self.ball_x > 680:
                distance_factor += 0.10
            elif self.ball_x > 600:
                distance_factor += 0.04
        else:
            if self.ball_x < 140:
                distance_factor += 0.16
            elif self.ball_x < 220:
                distance_factor += 0.10
            elif self.ball_x < 300:
                distance_factor += 0.04

        stamina = 0.0
        nearest, _ = self.find_nearest_player()
        if nearest is not None:
            stamina = max(0.0, min(0.06, (nearest["stamina"] - 50.0) / 800.0))

        keeper_penalty = 0.10

        prob = 0.12 + bias + role_bonus + distance_factor + stamina - keeper_penalty
        return max(0.08, min(0.62, prob))

    def _resolve_shot(self, team, role):
        minute = min(99, max(1, self.tick_count // 25))
        probability = self._shot_success_probability(team, role)

        if team == "home":
            save_stat_key = "away_saves"
            scorer_side = "home"
            scorer_name = self.home_team_name
        else:
            save_stat_key = "home_saves"
            scorer_side = "away"
            scorer_name = self.away_team_name

        if random.random() < probability:
            self.say(f"GOAL! {scorer_name} finish clinically.")
            self.timeline(minute, "goal", f"Goal for {scorer_name}")
            if self.goal_callback:
                self.goal_callback(scorer_side)
            self.last_goal_tick = self.tick_count
            self.reset_after_goal()
            return True

        if random.random() < 0.45:
            self.stats[save_stat_key] += 1
            self.say("Saved by the goalkeeper!")
            self.timeline(minute, "save", "Goalkeeper save.")
        else:
            self.say("Shot goes just wide.")
            self.timeline(minute, "chance", "Big chance missed.")

        return False

    def attempt_shot(self, team, role="ST"):
        if team == "home":
            goal_x = 895
            goal_y = random.randint(220, 280)
            self.stats["home_shots"] += 1
            self.stats["home_on_target"] += 1 if random.random() < 0.72 else 0
            color = "#ffb3b3"
        else:
            goal_x = 5
            goal_y = random.randint(220, 280)
            self.stats["away_shots"] += 1
            self.stats["away_on_target"] += 1 if random.random() < 0.72 else 0
            color = "#bcd9ff"

        self.draw_tracker_line(self.ball_x, self.ball_y, goal_x, goal_y, color, width=4)
        self.kick_ball_toward(goal_x, goal_y, power=random.uniform(9.0, 13.5))
        self.say("Shot taken!")
        self.last_shot_tick = self.tick_count
        self._resolve_shot(team, role)

    def maybe_action(self):
        nearest, dist = self.find_nearest_player()
        if nearest is None or dist > 42:
            return

        team = nearest["team"]
        role = nearest["role"]

        if team == "home":
            self.home_pos_ticks += 1
            tactic = self.home_tactic
            close_to_goal = self.ball_x > 620
            in_final_third = self.ball_x > 520
        else:
            self.away_pos_ticks += 1
            tactic = self.away_tactic
            close_to_goal = self.ball_x < 280
            in_final_third = self.ball_x < 380

        shot_bias = max(0.18, float(tactic.get("shot_bias", 0.18)))
        attacking_role = role in ("ST", "LW", "RW", "CAM", "LM", "RM", "CM")

        shot_roll = random.random()

        if attacking_role and close_to_goal and shot_roll < shot_bias:
            self.attempt_shot(team, role)
        elif attacking_role and in_final_third and shot_roll < shot_bias * 0.55:
            self.attempt_shot(team, role)
        else:
            self.pass_ball(team)

        minute = min(99, max(1, self.tick_count // 25))
        if random.random() < 0.025:
            self.timeline(minute, "card", "Yellow card shown.")
        if random.random() < 0.015:
            self.timeline(minute, "substitution", "Substitution made.")
        if random.random() < 0.03:
            self.timeline(minute, "manual", "Possession battle intensifies.")

    def move_ball(self):
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy

        self.ball_dx *= 0.978
        self.ball_dy *= 0.978

        if self.ball_img is not None:
            self.canvas.coords(self.ball, self.ball_x, self.ball_y)
        else:
            self.canvas.coords(self.ball, self.ball_x, self.ball_y, self.ball_x + 10, self.ball_y + 10)

    # ------------------------------------------------
    # GK / GOALS
    # ------------------------------------------------

    def goalkeeper_dive(self, keeper, direction):
        dive = 16 if direction == "right" else -16
        self.canvas.move(keeper["obj"], dive, 0)
        self.canvas.move(keeper["label"], dive, 0)
        self.canvas.move(keeper["role_label"], dive, 0)
        keeper["x"] += dive

    def maybe_goalkeeper_save(self):
        left_gk = self.goalkeeper_for("home")
        right_gk = self.goalkeeper_for("away")

        if self.ball_x < 80 and 180 < self.ball_y < 320 and left_gk:
            self.goalkeeper_dive(left_gk, "left")
            if random.random() < 0.35:
                self.ball_dx = abs(self.ball_dx) * 0.60
                self.ball_dy *= 0.50
                self.stats["home_saves"] += 1
                self.say("Great save by the home keeper!")
                return True

        if self.ball_x > 820 and 180 < self.ball_y < 320 and right_gk:
            self.goalkeeper_dive(right_gk, "right")
            if random.random() < 0.35:
                self.ball_dx = -abs(self.ball_dx) * 0.60
                self.ball_dy *= 0.50
                self.stats["away_saves"] += 1
                self.say("Brilliant save by the away keeper!")
                return True

        return False

    def check_goal(self):
        if self.ball_x <= 8 and 208 <= self.ball_y <= 292:
            if self.goal_callback:
                self.goal_callback("away")
            self.reset_after_goal()

        if self.ball_x >= 892 and 208 <= self.ball_y <= 292:
            if self.goal_callback:
                self.goal_callback("home")
            self.reset_after_goal()

    def reset_after_goal(self):
        self.ball_x = 450.0
        self.ball_y = 250.0
        self.ball_dx = 0.0
        self.ball_dy = 0.0
        if self.ball_img is not None:
            self.canvas.coords(self.ball, self.ball_x, self.ball_y)
        else:
            self.canvas.coords(self.ball, 445, 245, 455, 255)

    # ------------------------------------------------

    def animate(self):
        if not self.running:
            return

        try:
            self.tick_count += 1

            if self.tick_count % 30 == 0:
                self.clear_tracker_lines()

            self.move_players()

            if random.random() < 0.52:
                self.maybe_action()

            self.move_ball()

            if self.tick_count - self.last_goal_tick > 4:
                self.maybe_goalkeeper_save()
                self.check_goal()

            if self.tick_count % 15 == 0:
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
        self.last_shot_tick = -999
        self.last_goal_tick = -999

        self.draw_pitch()
        self.create_players()
        self.create_ball()
        self.push_possession()
        self.push_stats()