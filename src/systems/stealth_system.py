"""Calibrated numerical signals. No camera/microphone access and no engine imports."""
import math,statistics

class StealthSystem:
    duration=15.
    def __init__(self,noise_sensitivity=100,motion_sensitivity=100,elapsed=0.,danger=0.):
        self.noise_sensitivity=noise_sensitivity;self.motion_sensitivity=motion_sensitivity
        self.elapsed=elapsed;self.danger=danger;self.noise=0.;self.motion=0.
        self.calibration=0.;self.db_samples=[];self.motion_samples=[];self.noise_threshold=-32.;self.motion_threshold=.65
        self.noise_time=0.;self.motion_time=0.;self.cause=None
    def calibrate(self,dt,db,motion,reliable=True):
        if not reliable:return False
        dt=max(0,min(.2,dt));self.calibration+=dt
        self.db_samples.append(db);self.motion_samples.append(motion)
        if self.calibration>=2:
            self.noise_threshold=max(-55,min(-18,statistics.median(self.db_samples)+12))+(100-self.noise_sensitivity)*.1
            self.motion_threshold=max(.25,min(1.2,statistics.median(self.motion_samples)*3+.35))*100/self.motion_sensitivity
            return True
        return False
    def step(self,dt,db,motion,reliable=True):
        if self.cause:return self.cause
        if not reliable:return None
        dt=max(0,min(.2,dt));alpha=1-math.exp(-dt*7)
        self.noise+=alpha*(max(0,min(1,(db-self.noise_threshold+8)/24))-self.noise)
        self.motion+=alpha*(max(0,min(1,motion/max(.01,self.motion_threshold)))-self.motion)
        self.noise_time=max(0,self.noise_time+dt*(1 if db>self.noise_threshold else -2))
        self.motion_time=max(0,self.motion_time+dt*(1 if motion>self.motion_threshold else -2))
        alert=self.noise_time>.45 or self.motion_time>.35
        self.danger=max(0,min(1,self.danger+dt*(.55 if alert else -.18)))
        self.elapsed=min(self.duration,self.elapsed+dt)
        if self.danger>=1:self.cause='motion' if self.motion_time>self.noise_time else 'noise'
        elif self.elapsed>=self.duration-1e-8:self.cause='quiet'
        return self.cause

class QTESystem:
    """Edge-triggered input: a held/repeated key cannot advance the next prompt."""
    def __init__(self,definition,mode='standard',injured=False):
        self.definition=definition;self.elapsed=0.;self.held=set();self.presses=0;self.hold_time=0.;self.result=None;self.route='';self.blocked=set()
        self.limit=float('inf') if mode=='untimed' else (6. if mode=='easy' else 3.)
        if injured and mode=='standard':self.limit*=.85
    def key(self,key,down):
        if not down:self.held.discard(key);self.blocked.discard(key);return
        if key in self.held or key in self.blocked or self.result is not None:return
        self.held.add(key);d=self.definition
        if d['type']=='sequence':
            if key!=d['keys'][self.presses]:self.result=False
            else:
                self.presses+=1
                if self.presses==len(d['keys']):self.result=True
        elif d['type']=='direction':
            if key in ('a','d'):self.route='left' if key=='a' else 'right';self.result=True
            else:self.result=False
        elif key!=d['key']:self.result=False
        elif d['type']=='single':self.result=True
        elif d['type']=='burst':
            self.presses+=1
            if self.presses>=d['count']:self.result=True
    def update(self,dt):
        if self.result is not None:return self.result
        dt=max(0,dt);self.elapsed+=dt
        if self.definition['type']=='hold':
            if self.definition['key'] in self.held:self.hold_time+=dt
            else:self.hold_time=0
            if self.hold_time>=self.definition['seconds']:self.result=True
        if self.result is None and self.elapsed>=self.limit:self.result=False
        return self.result
