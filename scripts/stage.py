#!/usr/bin/env python3
"""Builds independent PortableApps folder from the original, unmodified upstream binary set."""
import argparse, configparser, hashlib, json, pathlib, shutil, struct, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'config/compatibility.json').read_text())

def pe(path):
    with open(path,'rb') as f:
        if f.read(2)!=b'MZ':return False
        f.seek(0x3c);off=struct.unpack('<I',f.read(4))[0]
        if off>1048576:return False
        f.seek(off);return f.read(4)==b'PE\0\0'

def conf(root):
    defaults=root/'App'/'DefaultData'/'Config'
    defaults.mkdir(parents=True,exist_ok=True)
    for name in ['Sandboxie.ini','Sandboxie-Plus.ini']:
        path=root/'App'/'Sandboxie'/name
        if not path.is_file():raise ValueError('Missing upstream portable setting '+name)
        content=path.read_bytes()
        # Preserve original upstream ini; replace only the NEW minimal default file if empty.
        if name=='Sandboxie.ini':
            if content.strip():
                # Cannot force portable sandbox placement over unfamiliar upstream defaults.
                raise ValueError('Upstream Sandboxie.ini no longer empty; storage policy needs human review')
            content=b'[GlobalSettings]\r\nFileRootPath=%SbieHome%\\..\\..\\Data\\Sandboxes\\%USER%\\%SANDBOX%\r\n\r\n[UserSettings_Portable]\r\n'
        (defaults/name).write_bytes(content)
        path.unlink()

def make(root, resolved, origin, launcher):
    if root.exists():raise ValueError('Refusing to overwrite staged PortableApps directory')
    app=root/'App'/'Sandboxie'
    shutil.copytree(origin,app)
    for rel in CFG['required_files']:
        if not (app/rel).is_file():raise ValueError('Required executable/driver missing: '+rel)
    if not pe(app/'SandMan.exe') or not pe(launcher):raise ValueError('Missing genuine Windows launcher/SandMan PE')
    conf(root)
    shutil.copy2(launcher,root/'SandboxiePlusPortable.exe')
    info=root/'App'/'AppInfo';info.mkdir(parents=True,exist_ok=True)
    # Icon is prepared from original upstream SandMan icon by separate Windows step.
    for file in ('appicon.ico','appicon_16.png','appicon_32.png'):
        if not (info/file).is_file(): pass
    vers=resolved['version'];parts=[int(p) for p in vers.split('.')]; version4='.'.join(map(str,(parts+[0]*4)[:4]))
    (info/'appinfo.ini').write_text(f'''[Format]\nType=PortableApps.comFormat\nVersion={CFG['portableapps_format_version']}\n\n[Details]\nName=Sandboxie Plus Portable\nAppID=SandboxiePlusPortable\nPublisher=David Xanatos (Xanasoft)\nHomepage=https://sandboxie-plus.com/\nCategory=Utilities\nDescription=Sandboxie Plus (portable payload; administrator-required driver/service)\nLanguage=Multilingual\n\n[License]\nShareable=true\nOpenSource=false\nFreeware=true\nCommercialUse=false\n\n[Version]\nPackageVersion={version4}\nDisplayVersion={vers} {CFG['package_revision']}\n\n[Control]\nIcons=1\nStart=SandboxiePlusPortable.exe\n''',encoding='utf-8')
    (root/'App'/'DefaultData'/'TraceGuard').mkdir(parents=True,exist_ok=True)
    (root/'Data'/'TraceGuard').mkdir(parents=True,exist_ok=True)
    (root/'Data'/'Sandboxes').mkdir(parents=True,exist_ok=True)
    (root/'Other'/'Source').mkdir(parents=True,exist_ok=True)
    lic=pathlib.Path('work/upstream-license/LICENSE.Plus')
    if lic.is_file():shutil.copy2(lic,root/'Other'/'Source'/'LICENSE.Plus')
    (root/'Other'/'Source'/'UPSTREAM.txt').write_text('Unmodified upstream binary set from '+resolved['asset_url']+'\nCommit: '+resolved['commit']+'\nSee LICENSE.Plus and source at '+resolved['release_url']+'\n',encoding='utf-8')
    (root/'Other'/'Source'/'builder-manifest.json').write_text(json.dumps(resolved,indent=2)+'\n')
    for source,output in [(pathlib.Path('work/upstream/integrity.json'),'upstream-integrity.json'),(pathlib.Path('work/launcher/launcher-build.json'),'launcher-build.json')]:
        if source.is_file():shutil.copy2(source,root/'Other'/'Source'/output)
    (root/'App'/'AppInfo'/'Launcher').mkdir(exist_ok=True)
    (root/'App'/'AppInfo'/'Launcher'/'SandboxiePlusPortable.ini').write_text('[Launch]\nProgramExecutable=Sandboxie\\SandMan.exe\n; Custom compiled launcher handles portable storage and recovery.\n')
    (root/'Other'/'Help.html').write_text('<h1>Sandboxie Plus Portable</h1><p>Requires admin for driver/service. See builder README.</p>')
    # Upstream payload manifest is a baseline for subsequent TraceGuard detection.
    manifest=sorted(p.relative_to(app).as_posix() for p in app.rglob('*') if p.is_file())
    (root/'App'/'AppInfo'/'payload-files.json').write_text(json.dumps(manifest,indent=2))
    if (root/'App'/'Sandboxie'/'Sandboxie.ini').exists():raise ValueError('Staged binary tree must not contain mutable config')

def zip_folder(root, target):
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        for p in [root]+sorted(root.rglob('*')):
            rel=p.relative_to(root.parent).as_posix()
            if p.is_dir():z.writestr(rel.rstrip('/')+'/',b'')
            else:z.write(p,rel)
    with zipfile.ZipFile(target) as z:
        if z.testzip():raise ValueError('ZIP integrity failure')

def main():
    p=argparse.ArgumentParser();p.add_argument('--resolved',default='work/resolved.json');p.add_argument('--origin',default='work/upstream/Extracted');p.add_argument('--launcher',default='work/launcher/SandboxiePlusPortable.exe');p.add_argument('--root',default='work/SandboxiePlusPortable');p.add_argument('--dist',default='dist');p.add_argument('--no-zip',action='store_true');p.add_argument('--zip-only',action='store_true');a=p.parse_args()
    r=json.loads(pathlib.Path(a.resolved).read_text());root=pathlib.Path(a.root)
    if not a.zip_only:make(root,r,pathlib.Path(a.origin),pathlib.Path(a.launcher))
    if not a.no_zip:
        name=f'SandboxiePlusPortable_{r["version"]}_{CFG["package_revision"]}_Win64.zip';out=pathlib.Path(a.dist)/name;zip_folder(root,out);print('PortableApps ZIP:',out)
if __name__=='__main__':main()
