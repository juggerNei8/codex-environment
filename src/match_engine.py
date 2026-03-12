import random
import math

class Player:

    def __init__(self,name,role,x,y):

        self.name=name
        self.role=role

        self.x=x
        self.y=y

        self.stamina=100
        self.has_ball=False

        self.passes=0
        self.shots=0
        self.goals=0


class MatchEngine:

    def __init__(self):

        self.players_red=[]
        self.players_blue=[]

        self.ball_owner=None

        self.stats={
            "red":{"shots":0,"passes":0,"goals":0},
            "blue":{"shots":0,"passes":0,"goals":0}
        }

        self.formations={
            "4-3-3":[
                ("GK",1),
                ("CB",2),
                ("LB",1),
                ("RB",1),
                ("CM",3),
                ("LW",1),
                ("RW",1),
                ("ST",1)
            ],

            "4-2-3-1":[
                ("GK",1),
                ("CB",2),
                ("LB",1),
                ("RB",1),
                ("CDM",2),
                ("CAM",3),
                ("ST",1)
            ]
        }

    # ------------------------------------------------

    def create_team(self,team,formation):

        players=[]

        roles=self.formations[formation]

        for role,count in roles:

            for i in range(count):

                name=f"{role}{i}"

                x=random.randint(100,800)
                y=random.randint(80,420)

                p=Player(name,role,x,y)

                players.append(p)

        if team=="red":
            self.players_red=players
        else:
            self.players_blue=players

    # ------------------------------------------------

    def select_pass_target(self,player,team):

        if team=="red":
            mates=self.players_red
        else:
            mates=self.players_blue

        target=random.choice(mates)

        return target

    # ------------------------------------------------

    def attempt_pass(self,player,team):

        target=self.select_pass_target(player,team)

        success=random.random()

        player.passes+=1
        self.stats[team]["passes"]+=1

        if success>0.2:
            target.has_ball=True
            player.has_ball=False
            return target

        return None

    # ------------------------------------------------

    def attempt_shot(self,player,team):

        chance=random.random()

        player.shots+=1
        self.stats[team]["shots"]+=1

        if chance>0.85:

            player.goals+=1
            self.stats[team]["goals"]+=1

            return "goal"

        return "miss"

    # ------------------------------------------------

    def reduce_stamina(self):

        for p in self.players_red+self.players_blue:

            p.stamina-=random.uniform(0.1,0.5)

            if p.stamina<20:
                p.stamina=20

    # ------------------------------------------------

    def get_match_stats(self):

        return self.stats