"""Local patrol NPCs pause at authored waypoints and stop for conversations."""
import pygame
from src.entities.player import Player
class PatrolNPC:
    def __init__(self,obj,nav,walls):
        self.obj=obj;self.nav=nav;self.walls=walls;self.actor=Player(pygame.Rect(obj['rect']).center)
        self.actor.SPEED=65;self.route=[];self.index=0;self.pause=1
        self.points=obj.get('patrol',[])
    def update(self,dt,player):
        if not self.points:return
        if self.actor.position.distance_to(player)<100:return
        dt=min(dt,.1);self.pause=max(0,self.pause-dt)
        if self.pause:return
        if not self.route:
            self.route=self.nav.path(self.actor.position,self.points[self.index],player)
            self.index=(self.index+1)%len(self.points)
            if not self.route:self.pause=2;return
        delta=self.route[0]-self.actor.position
        block=pygame.Rect(0,0,50,44);block.center=player
        self.actor.move(delta,min(dt,delta.length()/self.actor.SPEED),self.walls+[block])
        if delta.length()<3:
            self.route.pop(0)
            if not self.route:self.pause=3
        r=pygame.Rect(self.obj['rect']);r.center=self.actor.position;self.obj['rect']=list(r)
