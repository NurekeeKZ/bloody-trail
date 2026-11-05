# Local release packaging after PyInstaller succeeds; preserves existing source and saves.
from pathlib import Path
from importlib.metadata import distributions
import hashlib
import json
import shutil
import zipfile

root=Path(__file__).resolve().parents[1]
bundle=root/'dist/BloodyTrail'
if not (bundle/'BloodyTrail.exe').exists():raise SystemExit('Build BloodyTrail.spec first')
licenses=bundle/'THIRD_PARTY_LICENSES'
licenses.mkdir(exist_ok=True)
index=[]
for dist in distributions():
    name=dist.metadata.get('Name','unknown')
    found=[]
    for file in dist.files or []:
        if any(word in file.name.lower() for word in ('license','copying','notice')) and not str(file).endswith('.py'):
            source=Path(dist.locate_file(file))
            if not source.is_file() or source.stat().st_size>2_000_000:continue
            destination=licenses/name/Path(str(file))
            # Metadata path cannot escape the designated licence folder.
            if not destination.resolve().is_relative_to(licenses.resolve()):continue
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,destination);found.append(str(destination.relative_to(bundle)))
    index.append({'name':name,'version':dist.version,'license_files':found,
                  'homepage':dist.metadata.get('Home-page','')})
(licenses/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ('README.md','Final_Report.md','Final_Demo_Script.md','Presentation_Content.md'):
    source=root/name if name=='README.md' else root/'docs'/name
    if source.exists():shutil.copy2(source,bundle/name)
shutil.copytree(root/'docs',bundle/'docs',dirs_exist_ok=True,ignore=shutil.ignore_patterns('screenshots','*.png','build_log.txt'))
# Reference assets with unknown provenance and download archives are intentionally excluded.
assert not (bundle/'_internal/assets/reference').exists()
assert not list((bundle/'_internal/assets').rglob('*.zip'))
archive=root/'dist/BloodyTrail-Windows-x64-RC4.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as output:
    for path in sorted(bundle.rglob('*')):
        if path.is_file():output.write(path,Path('BloodyTrail')/path.relative_to(bundle))
sha=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
(archive.with_suffix('.sha256')).write_text(sha+'  '+archive.name+'\n',encoding='utf-8')
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha},indent=2))
