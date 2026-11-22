#!/usr/bin/env python3
import json,pathlib,struct,sys,zipfile,hashlib
from stage import pe
cfg=json.loads((pathlib.Path(__file__).resolve().parents[1]/'config/compatibility.json').read_text())

def safe_extract(zf, target):
    target=pathlib.Path(target).resolve();names=set()
    for z in zf.infolist():
        path=pathlib.PurePosixPath(z.filename)
        if path.is_absolute() or '..' in path.parts or ':' in z.filename or '\\' in z.filename or (z.external_attr>>16)&0o170000==0o120000:
            raise ValueError('Unsafe ZIP path or symlink: '+z.filename)
        if str(path).lower() in names:raise ValueError('Duplicate archive path: '+z.filename)
        names.add(str(path).lower())
        if not (target/path).resolve().is_relative_to(target):raise ValueError('ZIP traversal')
    zf.extractall(target)

def validate(root, original=None):
    root=pathlib.Path(root)
    must=['SandboxiePlusPortable.exe','App/AppInfo/appinfo.ini','App/AppInfo/appicon.ico','App/AppInfo/appicon_16.png','App/AppInfo/appicon_32.png','App/AppInfo/payload-files.json','App/DefaultData/Config/Sandboxie.ini','App/DefaultData/Config/Sandboxie-Plus.ini','Data/TraceGuard','Data/Sandboxes']
    for item in must:
        if not (root/item).exists():raise ValueError('Missing package content '+item)
    if not pe(root/'SandboxiePlusPortable.exe'):raise ValueError('Launcher is not a Windows PE')
    app=root/'App/Sandboxie'
    if original:
        # Validation requires identical bytes of upstream ORIGINAL binaries, no executable rewriting.
        original=pathlib.Path(original)
        for p in original.rglob('*'):
            if p.is_file() and p.suffix.lower() in ('.exe','.dll','.sys'):
                rel=p.relative_to(original)
                other=app/rel
                if not other.is_file() or hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256(other.read_bytes()).digest():raise ValueError('Original upstream binary was modified: '+str(rel))
    for rel in cfg['required_files']:
        if not (app/rel).is_file():raise ValueError('Missing runtime payload '+rel)
    for name in ('Sandboxie.ini','Sandboxie-Plus.ini'):
        if (app/name).exists():raise ValueError('Mutable settings accidentally packaged in managed application directory')
    ini=(root/'App/AppInfo/appinfo.ini').read_text()
    if 'AppID=SandboxiePlusPortable' not in ini:raise ValueError('Wrong app metadata')
    return True
if __name__=='__main__':
    validate(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None);print('PortableApps staging verified (static only; driver not executed)')
