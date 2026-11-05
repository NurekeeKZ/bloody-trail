"""Keep the prologue extension when regenerating the original campaign data."""
import json
from pathlib import Path

def upgrade():
    folder=Path(__file__).resolve().parents[1]/'src/data'
    extension=json.loads((folder/'prologue_evidence.json').read_text(encoding='utf-8'))
    for name in ('evidence','rules'):
        path=folder/(name+'.json');value=json.loads(path.read_text(encoding='utf-8'))
        if name=='evidence':value.update(extension[name])
        else:
            ids={r['id'] for r in extension[name]};value=[r for r in value if r['id'] not in ids]+extension[name]
        path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':upgrade()
