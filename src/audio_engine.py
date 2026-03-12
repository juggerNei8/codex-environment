class AudioEngine:
    def __init__(self):
        self.crowd_playing = False
        self.muted = False

    def set_muted(self, muted: bool):
        self.muted = muted

    def play_crowd(self):
        if self.muted:
            return
        if not self.crowd_playing:
            print("Crowd ambience playing...")
            self.crowd_playing = True

    def stop_crowd(self):
        self.crowd_playing = False

    def play_goal(self):
        if self.muted:
            return
        print("GOAL CROWD CHEER!")

    def play_whistle(self):
        if self.muted:
            return
        print("Referee whistle!")