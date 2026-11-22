"""Verified repackage: exact single release ZIP and checksum from caller's own repository."""
import hashlib,os,pathlib,re,subprocess,sys,zipfile
from importlib.machinery import SourceFileLoader
import importlib.util
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('validate',root/'scripts'/'package-validate.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def main():
    tag=os.environ['SOURCE_TAG'];asset=os.environ['SOURCE_ZIP'];new=os.environ['TARGET_TAG']
    if not re.fullmatch(r'portable-[A-Za-z0-9._-]+',tag):raise ValueError('Untrusted source tag name')
    if not re.fullmatch(r'SandboxiePlusPortable_[A-Za-z0-9._-]+\.zip',asset):raise ValueError('Source ZIP must be an exact safe Sandboxie Plus Portable filename')
    if not re.fullmatch(r'portable-[A-Za-z0-9._-]+',new) or tag==new:raise ValueError('New unique tag must start with portable-')
    subprocess.run(['gh','release','view',tag,'--json','tagName'],check=True)
    if subprocess.run(['gh','release','view',new],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:raise ValueError('Refusing to overwrite existing release tag')
    d=root/'work'/'repackage-download';d.mkdir(parents=True,exist_ok=False)
    subprocess.run(['gh','release','download',tag,'--pattern',asset,'--pattern','SHA256SUMS.txt','--dir',str(d)],check=True)
    f=d/asset;s=d/'SHA256SUMS.txt'
    if not f.is_file() or not s.is_file():raise ValueError('Missing expected ZIP or publisher checksums')
    entries=[]
    for line in s.read_text(encoding='utf-8-sig').splitlines():
        match=re.fullmatch(r'([0-9a-fA-F]{64})\s+\*?(.+)',line)
        if match:entries.append((match.group(2).strip(),match.group(1).lower()))
    hashes=[h for name,h in entries if name==asset]
    if len(hashes)!=1:raise ValueError('SHA256SUMS has no unique checksum for requested asset')
    if hashlib.sha256(f.read_bytes()).hexdigest()!=hashes[0]:raise ValueError('Source archive checksum mismatch')
    target=root/'work'/'SandboxiePlusPortable'
    with zipfile.ZipFile(f) as z:
        if z.testzip():raise ValueError('Source ZIP corrupt')
        v.safe_extract(z,root/'work')
    v.validate(target)
    print('Verified original release ZIP. Repackaging only; no app compilation.')
if __name__=='__main__':
    try:main()
    except Exception as e:print('REPACKAGE FAILED: '+str(e),file=sys.stderr);sys.exit(1)
