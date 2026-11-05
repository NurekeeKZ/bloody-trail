# Build from bloody_trail: python -m PyInstaller BloodyTrail.spec --noconfirm
from pathlib import Path
from PyInstaller.utils.hooks import collect_all
root = Path(SPECPATH)
datas=[(str(root/'assets/portraits'),'assets/portraits'),(str(root/'src/data'),'src/data'),(str(root/'assets/evidence'),'assets/evidence'),
       (str(root/'assets/rooms'),'assets/rooms'),
       (str(root/'assets/models/vosk-model-small-ru-0.22'),'assets/models/vosk-model-small-ru-0.22'),
       (str(root/'assets/models/voice_model_manifest.json'),'assets/models')]
binaries=[]
hiddenimports=[]
for package in ('vosk','sounddevice','_sounddevice_data','cv2'):
    d,b,h=collect_all(package)
    datas+=d;binaries+=b;hiddenimports+=h
a=Analysis([str(root/'main.py')],pathex=[str(root)],binaries=binaries,datas=datas,
           hiddenimports=hiddenimports,excludes=['matplotlib','tkinter','pytest'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='BloodyTrail',debug=False,
        bootloader_ignore_signals=False,strip=False,upx=False,console=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='BloodyTrail')
