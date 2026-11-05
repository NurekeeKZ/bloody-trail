"""Stable PortAudio selectors and PCM gain; no engine dependency or capture."""
from array import array


def microphones(sd):
    devices=sd.query_devices(); hosts=sd.query_hostapis(); counts={}; rows=[]
    for index, item in enumerate(devices):
        if item['max_input_channels']<1: continue
        name=item['name']; host=hosts[item['hostapi']]['name']
        base=host+' | '+name; ordinal=counts.get(base,0);counts[base]=ordinal+1
        rows.append({'key':base+' | '+str(ordinal), 'name':name+' ['+host+']', 'index':index})
    return rows


def resolve_input(sd, key):
    if not key: return None, ''
    match=next((d for d in microphones(sd) if d['key']==key),None)
    return (match['index'],'') if match else (None,'Выбранный микрофон отключён; используется системный вход.')


def supported_rate(sd, device):
    info=sd.query_devices(device,'input')
    for rate in dict.fromkeys([int(info['default_samplerate']),16000,48000,44100]):
        try:
            sd.check_input_settings(device=device,channels=1,dtype='int16',samplerate=rate)
            return rate
        except Exception: pass
    raise RuntimeError('Устройство не поддерживает mono PCM16 на доступных частотах')


def apply_gain(pcm, gain):
    if gain==100:return pcm
    return array('h',(max(-32768,min(32767,round(v*gain/100))) for v in array('h',pcm))).tobytes()
