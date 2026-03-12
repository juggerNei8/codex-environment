class AudioEngine:

    def __init__(self):

        self.crowd_playing = False

    # --------------------------------

    def play_crowd(self):

        if not self.crowd_playing:

            print("Crowd sound playing...")
            self.crowd_playing = True

    # --------------------------------

    def play_goal(self):

        print("GOAL!!! Crowd ROARS!")