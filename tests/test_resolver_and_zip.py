import unittest,sys,tempfile,json,pathlib,zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from resolve import choose_release,choose_asset,semver,validate_license,validate_installer_portable
from stage import zip_folder
from importlib.util import spec_from_file_location,module_from_spec
p=pathlib.Path(__file__).resolve().parents[1]/'scripts'/'package-validate.py';s=spec_from_file_location('validation',p);v=module_from_spec(s);s.loader.exec_module(v)

def asset(tag, name=None, size=24200000):
 return {'id':5,'name':name or f'Sandboxie-Plus-x64-{tag}.exe','size':size,'state':'uploaded',
         'browser_download_url':f'https://github.com/sandboxie-plus/Sandboxie/releases/download/{tag}/{name or f"Sandboxie-Plus-x64-{tag}.exe"}'}
def release(tag,prerelease=False,asset_list=None):
 return {'id':1,'tag_name':tag,'html_url':'https://github.com/sandboxie-plus/Sandboxie/releases/tag/'+tag,
         'prerelease':prerelease,'draft':False,'assets':asset_list if asset_list is not None else [asset(tag)]}
class ResolverTests(unittest.TestCase):
 def test_semver_numeric_order(self):
  self.assertEqual(choose_release([release('v1.9.10'),release('v1.19.1'),release('v1.19.0')])['tag_name'],'v1.19.1')
 def test_skip_prereleases_nightly(self):
  self.assertEqual(choose_release([release('v1.20.0',True),release('v1.19.1'),release('v1.21.0-beta')])['tag_name'],'v1.19.1')
 def test_asset_different_version(self):
  r=release('v3.7.9',asset_list=[asset('v3.7.9')])
  self.assertEqual(choose_asset(r)['id'],5)
 def test_asset_ambiguous_fails(self):
  r=release('v3.7.9',asset_list=[])
  with self.assertRaises(RuntimeError):choose_asset(r)
 def test_prerelease_only_fails(self):
  with self.assertRaises(RuntimeError):choose_release([release('v1.3.0-beta'),release('v1.4.0',True)])
 def test_reject_malicious_asset_url(self):
  r=release('v3.7.9',asset_list=[{**asset('v3.7.9'),'browser_download_url':'https://untrusted.example/a.exe'}])
  with self.assertRaises(RuntimeError):choose_asset(r)
class PlusEditionRegressions(unittest.TestCase):
 def test_classic_higher_major_version_is_not_selected(self):
  # Actual failure from GitHub Actions on 2026-11-22.
  classic=release('v5.40.1',asset_list=[asset('v5.40.1','SandboxieInstall64-v5.40.1.exe',3000000)])
  plus=release('v1.19.1',asset_list=[asset('v1.19.1'),asset('v1.19.1','Sandboxie-Plus-ARM64-v1.19.1.exe')])
  self.assertEqual(choose_release([classic,plus])['tag_name'],'v1.19.1')
  self.assertEqual(choose_asset(plus)['name'],'Sandboxie-Plus-x64-v1.19.1.exe')
 def test_mismatched_plus_asset_on_classic_version_tag_is_rejected(self):
  # Some historical dual-edition releases can have different Plus and Classic numbering.
  classic=release('v5.74.1',asset_list=[asset('v5.74.1','Sandboxie-Plus-x64-v1.19.1.exe')])
  self.assertEqual(choose_release([classic,release('v1.19.1')])['tag_name'],'v1.19.1')
 def test_matching_tag_without_versioned_asset_name(self):
  # Controlled rename still accepted when Plus/x64 identity and metadata remain clear.
  changed=release('v2.2.0',asset_list=[asset('v2.2.0','Sandboxie-Plus-x64-Setup.exe')])
  self.assertEqual(choose_release([changed])['tag_name'],'v2.2.0')
 def test_classic_only_fails_with_edition_diagnostic(self):
  with self.assertRaisesRegex(RuntimeError,'Classic-only'):
   choose_release([release('v5.40.1',asset_list=[asset('v5.40.1','SandboxieInstall64-v5.40.1.exe')])])
 def test_ambiguous_newest_plus_must_not_fall_back(self):
  newer=release('v2.1.0',asset_list=[asset('v2.1.0'),asset('v2.1.0','Sandboxie-Plus_x64-v2.1.0.exe')])
  found=choose_release([newer,release('v1.19.1')])
  self.assertEqual(found['tag_name'],'v2.1.0')
  with self.assertRaisesRegex(RuntimeError,'exactly one'): choose_asset(found)
 def test_newer_plus_release_with_renamed_compatible_asset(self):
  release2=release('v2.1.2',asset_list=[asset('v2.1.2','Sandboxie-Plus_x64_v2.1.2.exe')])
  self.assertEqual(choose_release([release('v1.19.1'),release2])['tag_name'],'v2.1.2')
 def test_license_casing_matches_upstream(self):
  validate_license('Permitted to redistribute the original unmodified binaries. Public distribution of self-compiled binaries is only permitted. A business certificate is required.')
 def test_missing_license_permission_fails_closed(self):
  with self.assertRaisesRegex(RuntimeError,'license terms changed'):
   validate_license('a license with no redistribution permission')

class ZipSafety(unittest.TestCase):
 def test_empty_nested_directories_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d)/'SandboxiePlusPortable';(root/'Data'/'Sandboxes'/'A'/'B'/'C').mkdir(parents=True)
   path=pathlib.Path(d)/'out.zip';zip_folder(root,path)
   with zipfile.ZipFile(path) as z:self.assertIn('SandboxiePlusPortable/Data/Sandboxes/A/B/C/',z.namelist())
 def test_archive_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'evil.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('../escape.txt','no')
   with zipfile.ZipFile(p) as z:
    with self.assertRaises(ValueError):v.safe_extract(z,pathlib.Path(d)/'dest')
 def test_duplicate_filename_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'dup.zip'
   with zipfile.ZipFile(p,'w') as z:
    z.writestr('foo.txt','x');z.writestr('FOO.txt','y')
   with zipfile.ZipFile(p) as z:
    with self.assertRaises(ValueError):v.safe_extract(z,pathlib.Path(d)/'dest')
if __name__=='__main__':unittest.main()

class StageSimulation(unittest.TestCase):
 def test_new_version_and_nonstandard_origin_folder(self):
  from stage import make
  import json
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);origin=d/'any-future-archive-root'/'relocated-extract';origin.mkdir(parents=True)
   # Synthetic PE test fixtures, not functional app binaries.
   pe=bytearray(128);pe[0:2]=b'MZ';pe[0x3c:0x40]=(64).to_bytes(4,'little');pe[64:68]=b'PE\0\0'
   from stage import CFG
   for rel in CFG['required_files']:
    f=origin/rel;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(pe)
   for n in ['Sandboxie.ini','Sandboxie-Plus.ini']:(origin/n).write_bytes(b'')
   launcher=d/'real-shaped-launcher.exe';launcher.write_bytes(pe)
   target=d/'not-hardcoded-version-dir'
   make(target,{'version':'11.28.3','asset_url':'https://github.com/sandboxie-plus/Sandboxie/releases/download/v11.28.3/test.exe','commit':'test','release_url':'https://example.com'},origin,launcher)
   self.assertTrue((target/'App'/'DefaultData'/'Config'/'Sandboxie.ini').exists())
   self.assertFalse((target/'App'/'Sandboxie'/'Sandboxie.ini').exists())
   self.assertTrue((target/'Data'/'Sandboxes').is_dir())
   ini=(target/'App'/'AppInfo'/'appinfo.ini').read_text()
   self.assertIn('11.28.3',ini)
   self.assertIn('11.28.3.0',ini)
 def test_changed_upstream_default_requires_review(self):
  from stage import make,CFG
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);origin=d/'new-layout';origin.mkdir();p=bytearray(128);p[:2]=b'MZ';p[0x3c:0x40]=(64).to_bytes(4,'little');p[64:68]=b'PE\0\0'
   for rel in CFG['required_files']:
    f=origin/rel;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(p)
   (origin/'Sandboxie.ini').write_text('[GlobalSettings]\nNewUpstreamConfig=1')
   (origin/'Sandboxie-Plus.ini').write_bytes(b'')
   exe=d/'launcher.exe';exe.write_bytes(p)
   with self.assertRaisesRegex(ValueError,'human review'):
    make(d/'stage',{'version':'2.0.0','asset_url':'https://example.com','commit':'x','release_url':'https://example.com'},origin,exe)


# Actual Inno Setup field arrangement seen at upstream v1.19.1: the source
# file and installation destination are independent fields.
UPSTREAM_INSTALLER_V1191 = r'''[Setup]
Uninstallable=not IsPortable
PrivilegesRequiredOverridesAllowed=commandline

[Files]
Source: ".\Release\{#MyAppSrc}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: ".\Sandboxie.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist; Check: IsPortable
Source: ".\Sandboxie-Plus.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist; Check: IsPortable

[INI]
Filename: "{app}\{#MyAppName}.ini"; Section: "Options"; Key: "UiLanguage"; Check: IsPortable

[Code]
function IsPortable(): Boolean;
begin
  if (ExpandConstant('{param:portable|0}') = '1') or Portable then begin
    Result := True;
  end;
end;
'''

class PortableInstallerSourceRegressions(unittest.TestCase):
 def test_actual_v1191_source_destdir_format_accepted(self):
  contract = validate_installer_portable(UPSTREAM_INSTALLER_V1191)
  self.assertEqual(contract['portable_ini_files'],['Sandboxie.ini','Sandboxie-Plus.ini'])
  self.assertEqual(contract['config_destination'],'{app}')
 def test_compatible_whitespace_and_case_variations(self):
  altered=UPSTREAM_INSTALLER_V1191.replace('DestDir: "{app}"','DestDir: "{APP}\\"').replace('Check: IsPortable','Check: ( IsPortable )')
  self.assertTrue(validate_installer_portable(altered))
 def test_missing_plus_ini_fails(self):
  text=UPSTREAM_INSTALLER_V1191.replace('Source: ".\\Sandboxie-Plus.ini";', 'Source: ".\\ChangedPlus.ini";')
  with self.assertRaisesRegex(RuntimeError, 'Sandboxie-Plus.ini'):
   validate_installer_portable(text)
 def test_nonportable_only_ini_fails(self):
  text=UPSTREAM_INSTALLER_V1191.replace('onlyifdoesntexist; Check: IsPortable', 'onlyifdoesntexist; Check: not IsPortable')
  with self.assertRaisesRegex(RuntimeError, 'portable mode'):
   validate_installer_portable(text)
 def test_non_app_storage_target_fails(self):
  text=UPSTREAM_INSTALLER_V1191.replace('Source: ".\\Sandboxie-Plus.ini"; DestDir: "{app}"', 'Source: ".\\Sandboxie-Plus.ini"; DestDir: "{localappdata}"')
  with self.assertRaisesRegex(RuntimeError, 'destination changed'):
   validate_installer_portable(text)
 def test_overwrite_existing_settings_fails(self):
  text=UPSTREAM_INSTALLER_V1191.replace('ignoreversion onlyifdoesntexist; Check: IsPortable', 'ignoreversion; Check: IsPortable')
  with self.assertRaisesRegex(RuntimeError, 'overwrite'):
   validate_installer_portable(text)
 def test_duplicate_configuration_entry_fails(self):
  row='Source: ".\\Sandboxie.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist; Check: IsPortable'
  text=UPSTREAM_INSTALLER_V1191.replace(row,row+'\n'+row)
  with self.assertRaisesRegex(RuntimeError, 'expected one'):
   validate_installer_portable(text)
 def test_mentions_in_comments_do_not_count(self):
  text=UPSTREAM_INSTALLER_V1191.replace('Source: ".\\Sandboxie-Plus.ini";', '; Source: ".\\Sandboxie-Plus.ini";')
  with self.assertRaisesRegex(RuntimeError, 'Sandboxie-Plus.ini'):
   validate_installer_portable(text)
