"""Grid A*: no diagonals, footprint-expanded obstacles, bounded reachable search."""
import heapq
from collections import deque
import pygame

class NPCPathfinding:
    CELL=24
    def __init__(self,size,walls):
        self.size=size;self.walls=[pygame.Rect(w) for w in walls]
        self.free=set()
        for y in range(size[1]//self.CELL):
            for x in range(size[0]//self.CELL):
                p=self.point((x,y));r=pygame.Rect(0,0,28,22);r.center=p
                if not any(r.colliderect(w) for w in self.walls):self.free.add((x,y))
    def point(self,node):return pygame.Vector2((node[0]+.5)*self.CELL,(node[1]+.5)*self.CELL)
    def cell(self,p):return int(p[0]//self.CELL),int(p[1]//self.CELL)
    def nearest(self,p):return min(self.free,key=lambda n:self.point(n).distance_squared_to(p))
    def neighbors(self,n):
        return [p for p in ((n[0]+1,n[1]),(n[0]-1,n[1]),(n[0],n[1]+1),(n[0],n[1]-1)) if p in self.free]
    def reachable(self,start):
        seen={start};queue=deque([start])
        while queue:
            for n in self.neighbors(queue.popleft()):
                if n not in seen:seen.add(n);queue.append(n)
        return seen
    def path(self,start,end,avoid=None):
        start=self.nearest(start);end=self.nearest(end)
        queue=[(0,start)];cost={start:0};previous={}
        while queue:
            _,node=heapq.heappop(queue)
            if node==end:
                result=[]
                while node!=start:result.append(self.point(node));node=previous[node]
                return list(reversed(result))
            for neighbor in self.neighbors(node):
                if avoid is not None and self.point(neighbor).distance_to(avoid)<40:continue
                score=cost[node]+1
                if score<cost.get(neighbor,float('inf')):
                    cost[neighbor]=score;previous[neighbor]=node
                    heapq.heappush(queue,(score+abs(neighbor[0]-end[0])+abs(neighbor[1]-end[1]),neighbor))
        return []
