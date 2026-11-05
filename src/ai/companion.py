"""Companion motion runs only in exploration; state belongs to the save, not UI."""
import random
import pygame
from src.ai.pathfinding import NPCPathfinding
from src.entities.player import Player
MODES={'follow':'Следуй за мной','roam':'Исследуй территорию','stay':'Оставайся здесь','come':'Подойди ко мне'}

class CompanionAI:
    def __init__(self,state,world,walls):
        self.state=state;self.nav=NPCPathfinding(world['size'],walls);self.walls=walls
        self.saved=state.companion;self.route=[];self.age=0;self.pause=0;self.rng=random.Random(state.location)
        origin=self.saved['position']
        people=[pygame.Rect(o['rect']).center for o in world['objects'] if o['kind']=='dialogue']
        if self.saved['location']!=state.location or self.nav.cell(origin) not in self.nav.free or any(pygame.Vector2(origin).distance_to(p)<65 for p in people):
            reachable=self.nav.reachable(self.nav.nearest(state.position))
            reachable={n for n in reachable if all(self.nav.point(n).distance_to(p)>75 for p in people)}
            node=min(reachable,key=lambda n:abs(self.nav.point(n).distance_to(state.position)-70))
            origin=self.nav.point(node)
        self.actor=Player(origin);self.actor.SPEED=190
        self.saved.update(location=state.location,position=list(self.actor.position))
        self.reachable=self.nav.reachable(self.nav.nearest(origin))

    def command(self,mode):
        if mode not in MODES:raise ValueError('Unknown companion mode')
        self.saved['mode']=mode;self.route=[];self.age=1;self.pause=0

    def update(self,dt,player,obstacles=()):
        dt=min(dt,.1);self.age+=dt;self.pause=max(0,self.pause-dt)
        mode=self.saved['mode'];distance=self.actor.position.distance_to(player)
        if mode=='stay':return
        if mode in ('follow','come') and distance<65:
            self.route=[]
            if mode=='come':self.saved['mode']='follow'
            return
        if self.age>.7 and self.pause==0:
            self.age=0
            if mode=='roam':
                if not self.route:
                    candidates=[n for n in self.reachable if self.nav.point(n).distance_to(player)>65]
                    if candidates:self.route=self.nav.path(self.actor.position,self.nav.point(self.rng.choice(sorted(candidates))),player)
            else:
                candidates=[n for n in self.reachable if 60<=self.nav.point(n).distance_to(player)<=100]
                if candidates:
                    goal=min(candidates,key=lambda n:self.nav.point(n).distance_to(self.actor.position))
                    self.route=self.nav.path(self.actor.position,self.nav.point(goal),player)
        if self.route:
            target=self.route[0];delta=target-self.actor.position
            step=min(dt,delta.length()/self.actor.SPEED)
            block=pygame.Rect(0,0,60,52);block.center=player
            self.actor.move(delta,step,self.walls+[block]+list(obstacles))
            if self.actor.position.distance_to(target)<2:
                self.route.pop(0)
                if not self.route and mode=='roam':self.pause=2.5
        self.saved['position']=list(self.actor.position)
