#!/usr/bin/env python3
"""Only official stable GitHub releases, source-checked at the release's actual tag commit."""
import argparse, json, os, pathlib, re, subprocess, sys, time, urllib.request, urllib.error
CFG = json.loads((pathlib.Path(__file__).resolve().parents[1]/'config'/'compatibility.json').read_text())
API = 'https://api.github.com'

def api(path):
    assert path.startswith('/repos/sandboxie-plus/Sandboxie/')
    req=urllib.request.Request(API+path,headers={'Accept':'application/vnd.github+json','User-Agent':'Sandboxie-PortableApps-Builder/1','X-GitHub-Api-Version':'2022-11-28', **({'Authorization':'Bearer '+os.environ['GH_TOKEN']} if os.environ.get('GH_TOKEN') else {})})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req,timeout=30) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429,500,502,503,504) and attempt<3: time.sleep(2**attempt);continue
            raise RuntimeError(f'GitHub API failed HTTP {e.code}: {path}') from e
        except (TimeoutError, urllib.error.URLError):
            if attempt==3: raise
            time.sleep(2**attempt)

def semver(tag):
    match=re.fullmatch(CFG['stable_version_regex'],tag)
    return tuple(int(x) for x in match['version'].split('.')) if match else None

def plus_assets(release):
    """Find official Plus-x64 assets that actually belong to the release's Plus version.

    Classic versions are a separate sequence; for dual-edition tags, a Plus asset
    with a different embedded version must not be ranked using the Classic tag.
    """
    tag_version = semver(release.get('tag_name', ''))
    result = []
    for a in release.get('assets', []):
        name = a.get('name', '')
        if not re.fullmatch(CFG['asset_regex'], name): continue
        if re.search(CFG['exclude_asset_regex'], name): continue
        if a.get('size', 0) <= 1_000_000: continue
        if a.get('state', 'uploaded') != 'uploaded': continue
        # If an asset filename states a version, it must match the release tag.
        # This permits compatible name changes without requiring a version token.
        found = re.findall(r'(?<!\d)(\d+\.\d+\.\d+)(?!\d)', name)
        if found and (tag_version is None or any(tuple(map(int, v.split('.'))) != tag_version for v in found)):
            continue
        result.append(a)
    return result

def choose_release(releases):
    stable = [r for r in releases if not r.get('draft') and not r.get('prerelease')
              and semver(r.get('tag_name', ''))]
    if not stable:
        raise RuntimeError('No stable version tags (vX.Y.Z) were found in the requested releases')
    # The same repository publishes Classic 5.x and Plus 1.x releases. Only compare
    # versions *after* the edition is established by its official release assets.
    eligible = [r for r in stable if plus_assets(r)]
    if not eligible:
        names = [f"{r['tag_name']}: {[a.get('name') for a in r.get('assets', [])]}"
                 for r in sorted(stable, key=lambda r: semver(r['tag_name']), reverse=True)[:5]]
        raise RuntimeError('No eligible stable Sandboxie PLUS x64 installer release found. '
                           'Classic-only releases cannot be used. Sample assets: '+repr(names))
    # A newer matching release with ambiguous Plus-x64 assets must fail during
    # choose_asset, rather than silently rolling back to an older edition.
    return max(eligible, key=lambda r: semver(r['tag_name']))

def choose_asset(release):
    xs=plus_assets(release)
    if len(xs)!=1:raise RuntimeError(f"Expected exactly one official Plus x64 installer, found {len(xs)}: {[a.get('name') for a in release.get('assets',[])]}")
    a=xs[0]
    if a.get('browser_download_url','').split('/')[2]!='github.com': raise RuntimeError('Untrusted asset URL host')
    expected=f"https://github.com/{CFG['upstream_repository']}/releases/download/{release['tag_name']}/"
    if not a['browser_download_url'].startswith(expected):raise RuntimeError('Asset is not from the selected official tag')
    digest=a.get('digest') or ''
    if digest and not re.fullmatch(r'sha256:[0-9a-fA-F]{64}',digest):raise RuntimeError('Unexpected upstream asset digest format')
    return a

def tag_sha(tag):
    out=subprocess.check_output(['git','ls-remote','--tags','https://github.com/sandboxie-plus/Sandboxie.git',f'refs/tags/{tag}',f'refs/tags/{tag}^{{}}'],text=True,timeout=40)
    rows=dict(line.split('\t',1)[::-1] for line in out.strip().splitlines() if '\t' in line)
    commit=rows.get(f'refs/tags/{tag}^{{}}') or rows.get(f'refs/tags/{tag}')
    if not commit or not re.fullmatch('[0-9a-f]{40}',commit): raise RuntimeError('Cannot resolve the exact upstream tag to a Git commit')
    return commit

def validate_license(lic):
    # Upstream uses "Public distribution..." with an uppercase P in v1.19.1.
    # Wording is still checked fail-closed; capitalization must not alter rights.
    required = ('redistribute the original unmodified',
                'public distribution of self-compiled binaries',
                'business certificate')
    missing = [item for item in required if item not in lic.casefold()]
    if missing:
        raise RuntimeError('Plus license terms changed: manual redistribution review required; missing '+repr(missing))

def validate_installer_portable(iss):
    """Validate Inno Setup *semantics* instead of a guessed concatenated path.

    Inno's Source and DestDir are separate fields. In v1.19.1 the installer
    uses Source: ".\\Sandboxie-Plus.ini"; DestDir: "{app}", not the literal
    string "{app}\\Sandboxie-Plus.ini". Matching that nonexistent string
    falsely rejected the genuine portable installer.

    This is a deliberately narrow, fail-closed validator, not a full Inno
    interpreter. Macro-substituted/dynamic source paths require human review.
    """
    required_signals = (
        r'Uninstallable=not IsPortable',
        r'PrivilegesRequiredOverridesAllowed=commandline',
        r'{param:portable|0}',
        r'function IsPortable()',
    )
    for marker in required_signals:
        if marker.casefold() not in iss.casefold():
            raise RuntimeError('Upstream portable installer contract changed: missing ' + marker)

    # Only interpret real [Files] entries, not unrelated [INI], comments, or
    # incidental mentions in the documentation or Pascal code section.
    header = re.search(r'(?im)^\s*\[Files\]\s*$', iss)
    if not header:
        raise RuntimeError('Upstream installer has no [Files] section')
    rest = iss[header.end():]
    end = re.search(r'(?m)^\s*\[[A-Za-z][\w ]*\]\s*$', rest)
    block = rest[:end.start()] if end else rest

    entries = []
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith(';') or line.startswith('//') or line.startswith('#'):
            continue
        # Inno [Files] fields are written as Key: "value" or Key: value.
        fields = {}
        for m in re.finditer(r'\b(Source|DestDir|DestName|Flags|Check)\s*:\s*(?:"([^"]*)"|([^;]+))', line, re.I):
            fields[m.group(1).lower()] = (m.group(2) if m.group(2) is not None else m.group(3)).strip()
        if 'source' in fields:
            entries.append(fields)

    expected = ('Sandboxie.ini', 'Sandboxie-Plus.ini')
    for filename in expected:
        # File names are case insensitive on Windows. Both a relative Source
        # and explicitly rooted Source are accepted; no variable substitution
        # is attempted because it would hide incompatible future changes.
        matches = [f for f in entries if f.get('source','').replace('/', '\\').rsplit('\\',1)[-1].casefold() == filename.casefold()]
        if len(matches) != 1:
            raise RuntimeError(f'Upstream portable installer configuration changed: expected one [Files] Source for {filename}, found {len(matches)}')
        entry=matches[0]
        dest=entry.get('destdir','').rstrip('\\/').casefold()
        if dest != '{app}':
            raise RuntimeError(f'Upstream portable installer config destination changed for {filename}: {entry.get("destdir")}')
        if entry.get('destname',filename).casefold()!=filename.casefold():
            raise RuntimeError(f'Upstream portable installer config filename changed for {filename}')
        check=re.sub(r'[\s()]','',entry.get('check','')).casefold()
        if check!='isportable':
            raise RuntimeError(f'Upstream installer no longer restricts {filename} to portable mode')
        flags={f.casefold() for f in entry.get('flags','').split()}
        if 'onlyifdoesntexist' not in flags:
            raise RuntimeError(f'Upstream installer may overwrite an existing portable {filename}')
    return {'portable_ini_files': list(expected), 'config_destination': '{app}', 'source_analysis': 'Inno [Files] Source/DestDir/Flags/Check'}

def source_check(commit):
    base=f'/repos/{CFG["upstream_repository"]}/contents/'
    # GitHub Contents API returns base64 text. The license and installer script are checked against the *tag commit*.
    import base64
    def get(p):
        x=api(base+p+'?ref='+commit)
        if x.get('encoding')!='base64':raise RuntimeError(f'Cannot inspect {p}')
        return base64.b64decode(x['content']).decode('utf-8-sig')
    lic=get(CFG['source_license_path'])
    path=pathlib.Path('work/upstream-license/LICENSE.Plus');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(lic,encoding='utf-8')
    validate_license(lic)
    iss=get(CFG['source_installer_path'])
    portable_contract=validate_installer_portable(iss)
    return {'license_sha256':__import__('hashlib').sha256(lic.encode()).hexdigest(),'installer_script_sha256':__import__('hashlib').sha256(iss.encode()).hexdigest(), 'portable_installer_contract': portable_contract}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='work/resolved.json');p.add_argument('--tag',default='');p.add_argument('--offline-fixture');a=p.parse_args()
    if a.offline_fixture:
        releases=json.loads(pathlib.Path(a.offline_fixture).read_text())
    elif a.tag:
        # Explicit tags are resolved directly, even when too old for the first 300 releases.
        # Validate tag syntax before embedding it in an API URL.
        if not semver(a.tag): raise RuntimeError('Explicit upstream tag must be stable vX.Y.Z')
        releases=[api(f'/repos/{CFG["upstream_repository"]}/releases/tags/{a.tag}')]
    else:
        releases=[]
        for page in range(1,4):
            batch=api(f'/repos/{CFG["upstream_repository"]}/releases?per_page=100&page={page}')
            releases+=batch
            if len(batch)<100: break
    release=choose_release([r for r in releases if not a.tag or r['tag_name']==a.tag]);asset=choose_asset(release)
    sha=tag_sha(release['tag_name']) if not a.offline_fixture else 'fixture-not-a-commit'
    verification=source_check(sha) if not a.offline_fixture else {'test_fixture':True}
    result={'tag':release['tag_name'],'version':release['tag_name'].lstrip('v'),'commit':sha,'release_id':release['id'],'release_url':release['html_url'],'asset_id':asset['id'],'asset_name':asset['name'],'asset_url':asset['browser_download_url'],'asset_size':asset['size'],'asset_digest':asset.get('digest') or '', 'verification':verification,'package_revision':CFG['package_revision'],'source_mode':CFG['source_mode']}
    dest=pathlib.Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:
            for key in ('version','tag','commit','package_revision'): f.write(f'{key}={result[key]}\n')
if __name__=='__main__':
    try:main()
    except Exception as e:print(f'PREFLIGHT FAILED: {e}',file=sys.stderr);sys.exit(1)
