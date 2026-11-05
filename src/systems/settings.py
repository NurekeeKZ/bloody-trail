"""Local preferences. Sensor consent never starts a device or changes OS permissions."""
import json
from dataclasses import dataclass, asdict


@dataclass
class Settings:
    volume: int = 60
    music_volume: int = 100
    environment_volume: int = 100
    dialogue_volume: int = 100
    effects_volume: int = 100
    rain_volume: int = 40
    microphone_device: str = ''
    output_device: str = ''
    microphone_gain: int = 100
    text_speed: int = 48
    controls: str = 'both'
    fullscreen: bool = False
    qte_mode: str = 'standard'
    microphone_consent: bool = False
    camera_consent: bool = False
    reduced_motion: bool = False
    stealth_noise_sensitivity: int = 100
    stealth_motion_sensitivity: int = 100
    stealth_manual: bool = True


class SettingsManager:
    def __init__(self, path):
        self.path = path
        self.value = Settings()
        self.error = ''
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding='utf-8'))
                value = Settings(**raw)
                if type(value.volume) is not int or not 0 <= value.volume <= 100:
                    raise ValueError('volume')
                for key in ('music_volume', 'environment_volume', 'dialogue_volume', 'effects_volume', 'rain_volume'):
                    if type(getattr(value,key)) is not int or not 0 <= getattr(value,key) <= 100: raise ValueError(key)
                for key in ('stealth_noise_sensitivity','stealth_motion_sensitivity'):
                    if type(getattr(value,key)) is not int or not 50<=getattr(value,key)<=150: raise ValueError(key)
                if type(value.stealth_manual) is not bool: raise ValueError('stealth_manual')
                if type(value.microphone_gain) is not int or not 25 <= value.microphone_gain <= 400: raise ValueError('gain')
                if type(value.text_speed) is not int or not 16 <= value.text_speed <= 96: raise ValueError('text speed')
                if any(not isinstance(getattr(value,k), str) for k in ('microphone_device','output_device')): raise ValueError('device')
                if value.controls not in ('both', 'wasd', 'arrows') or value.qte_mode not in ('standard', 'easy', 'untimed'):
                    raise ValueError('mode')
                if any(type(getattr(value, k)) is not bool for k in ('fullscreen', 'microphone_consent', 'camera_consent', 'reduced_motion')):
                    raise ValueError('boolean')
                self.value = value
            except (ValueError, TypeError, OSError):
                self.error = 'Настройки повреждены: применены безопасные значения по умолчанию.'

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(asdict(self.value), ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(self.path)
