"""Explicit, optional model download. Never called on game startup."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1] / 'assets/models'
NAME = 'vosk-model-small-ru-0.22'
URL = 'https://alphacephei.com/vosk/models/' + NAME + '.zip'


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    if (ROOT / NAME / 'am/final.mdl').exists():
        print('Model already available:', ROOT / NAME)
        return
    archive = ROOT / (NAME + '.zip')
    with urllib.request.urlopen(URL, timeout=60) as response, archive.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            target = (ROOT / item.filename).resolve()
            if not target.is_relative_to(ROOT.resolve()) or not item.filename.startswith(NAME + '/'):
                raise ValueError('Unsafe model archive path')
        bundle.extractall(ROOT)
    (ROOT / 'voice_model_manifest.json').write_text(json.dumps({'url': URL, 'sha256_downloaded': digest,
        'license': 'Apache-2.0', 'model': NAME}, indent=2), encoding='utf-8')
    print('Local model ready:', ROOT / NAME, 'SHA256:', digest)


if __name__ == '__main__':
    main()
