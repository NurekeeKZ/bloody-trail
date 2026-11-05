import math
import random
from array import array
import pygame


class AudioManager:
    """Original short synthesized UI tones; gracefully silent without an audio device."""
    _loops = {}

    def __init__(self):
        self.sounds = {}
        self.mode = None
        self.settings = None
        self.error = ''
        self.levels = [0.0,0.0]
        self.duck = False
        self.suspended = False
        self.volume = 0.6
        self.available = pygame.mixer.get_init() is not None
        if self.available:
            rate, fmt, channels = pygame.mixer.get_init()
            if fmt != -16:
                self.available = False
                return
            for name, frequency, duration in [('heartbeat', 58, .22), ('hover', 660, 0.035), ('click', 440, 0.075), ('evidence', 880, 0.3), ('step', 90, 0.06), ('door', 145, .6), ('glass', 1700, .3), ('struggle', 65, .4), ('memory', 1046, .8), ('dialogue', 250, .045), ('whisper', 180, .8)]:
                count = int(rate * duration)
                samples = array('h')
                rng = random.Random(name)
                for i in range(count):
                    envelope = min(1, i / (rate * 0.004)) * (1 - i / count)
                    wave = math.sin(2 * math.pi * frequency * i / rate)
                    if name=='glass': wave=.75*rng.uniform(-1,1)+.25*math.sin(2*math.pi*3200*i/rate)
                    elif name=='struggle': wave=.6*wave+.4*rng.uniform(-1,1)
                    elif name=='door': wave=math.sin(2*math.pi*(frequency*i/rate+22*(i/rate)**2))*(.5+.5*math.sin(i/190)**2)
                    elif name=='whisper': wave=(.6*wave+.3*math.sin(2*math.pi*570*i/rate))*(.5+.5*math.sin(i/1700)**2)
                    value = int(5000 * wave * envelope)
                    samples.extend([value] * channels)
                self.sounds[name] = pygame.mixer.Sound(buffer=samples)
            pygame.mixer.set_reserved(3)

    def apply(self, settings):
        self.settings = settings
        self.volume = settings.volume / 100

    def factor(self, name):
        return getattr(self.settings, name, 100) / 100

    def play(self, name):
        if name in self.sounds and self.volume > 0 and not self.suspended:
            category = 'dialogue_volume' if name == 'dialogue' else 'effects_volume'
            self.sounds[name].set_volume(self.volume * self.factor(category))
            self.sounds[name].play()

    @staticmethod
    def output_devices():
        try:
            from pygame._sdl2.audio import get_audio_device_names
            return list(get_audio_device_names(False)), ''
        except Exception as exc:
            return [], str(exc)

    def switch_output(self, name):
        settings = self.settings
        try:
            pygame.mixer.quit()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, devicename=name or None)
            self.__init__()
            if settings: self.apply(settings)
            return True
        except (pygame.error, OSError) as exc:
            error = str(exc)
            try: pygame.mixer.init(frequency=44100,size=-16,channels=2)
            except pygame.error: pass
            self.__init__()
            if settings: self.apply(settings)
            self.error = 'Выход недоступен; применён системный выход: ' + error
            return False

    def ambience(self, mode, dt=.016, duck=False):
        if not self.available: return
        self.duck = duck
        self.suspended = mode == 'silent'
        self.mode = mode
        targets = [0.0, 0.0]
        if mode in ('rain','prologue','aftermath'):
            targets[0] = self.volume * .28 * self.factor('environment_volume') * self.factor('rain_volume') * (.3 if duck or mode != 'rain' else 1)
        if mode in ('menu','prologue'):
            targets[1] = self.volume * .28 * self.factor('music_volume') * (.45 if mode == 'prologue' else 1)
        for i, (name, target) in enumerate(zip(('rain','menu'), targets)):
            channel = pygame.mixer.Channel(i)
            if self.suspended:
                channel.stop();self.levels[i]=0
                continue
            self.levels[i] += (target-self.levels[i]) * min(1,max(0,dt)*4)
            if target > 0 and not channel.get_busy():
                if name not in self.sounds: self.sounds[name]=self.loop(name)
                channel.set_volume(0)
                channel.play(self.sounds[name],loops=-1)
            channel.set_volume(self.levels[i])
            if target == 0 and self.levels[i]<.001: channel.stop();self.levels[i]=0

    def loop(self, mode):
        rate, _, channels = pygame.mixer.get_init()
        key = (mode, rate, channels)
        if key not in self._loops:
            rng = random.Random(2035)
            samples = array('h')
            notes = (110,130.81,146.83,123.47)
            count = rate * 4
            for i in range(count):
                if mode == 'rain':
                    value = rng.randint(-2200,2200)
                else:
                    phase = (i % rate) / rate
                    frequency = notes[i // rate]
                    value = int(3500 * math.sin(math.pi * phase) ** 2 *
                                (math.sin(2*math.pi*frequency*i/rate) + .3*math.sin(4*math.pi*frequency*i/rate)))
                samples.extend([value]*channels)
            self._loops[key] = samples.tobytes()
        return pygame.mixer.Sound(buffer=self._loops[key])

    def location_ambience(self,location):
        if not self.available:return
        channel=pygame.mixer.Channel(2)
        if not location or self.suspended:
            channel.stop();self.location_mode=None;return
        if getattr(self,'location_mode',None)!=location:
            rate,_,channels=pygame.mixer.get_init()
            key='location_'+location
            if key not in self.sounds:
                frequencies={'station':95,'apartment':160,'archive':73,'metro':46,'helios':120,'port':55}
                frequency=frequencies[location];samples=array('h');rng=random.Random(location)
                for i in range(rate*3):
                    t=i/rate;wave=.25*math.sin(2*math.pi*frequency*t)
                    if location=='metro':wave+=.2*rng.uniform(-1,1)+.2*math.sin(2*math.pi*660*t)*max(0,1-abs(t-1.5)*8)
                    elif location=='port':wave+=.2*rng.uniform(-1,1)+.2*math.sin(2*math.pi*110*t)*math.sin(math.pi*t/3)**2
                    elif location=='apartment':wave+=.15*math.sin(2*math.pi*650*t)*max(0,1-(t%1)*30)
                    samples.extend([int(1800*wave)]*channels)
                self.sounds[key]=pygame.mixer.Sound(buffer=samples)
            channel.play(self.sounds[key],loops=-1);self.location_mode=location
        channel.set_volume(self.volume*self.factor('environment_volume')*(.25 if self.duck else .65))
