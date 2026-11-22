import unittest,sys,tempfile,json,pathlib,zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
from resolve import choose_release,choose_asset,semver
from stage import zip_folder
from importlib.util import spec_from_file_location,module_from_spec
p=pathlib.Path(__file__).resolve().parents[1]/'scripts'/'package-validate.py';s=spec_from_file_location('validation',p);v=module_from_spec(s);s.loader.exec_module(v)

def release(tag,prerelease=False,asset=None):return {'id':1,'tag_name':tag,'html_url':'https://github.com/sandboxie-plus/Sandboxie/releases/tag/'+tag,'prerelease':prerelease,'draft':False,'assets':asset or []}
class ResolverTests(unittest.TestCase):
 def test_semver_numeric_order(self):
  self.assertEqual(choose_release([release('v1.9.10'),release('v1.19.1'),release('v1.19.0')])['tag_name'],'v1.19.1')
 def test_skip_prereleases_nightly(self):
  self.assertEqual(choose_release([release('v1.20.0',True),release('v1.19.1'),release('v1.21.0-beta')])['tag_name'],'v1.19.1')
 def test_asset_different_version(self):
  r=release('v3.7.9',asset=[{'id':5,'name':'Sandboxie-Plus-x64-v3.7.9.exe','size':10000000,'state':'uploaded','browser_download_url':'https://github.com/sandboxie-plus/Sandboxie/releases/download/v3.7.9/Sandboxie-Plus-x64-v3.7.9.exe'}])
  self.assertEqual(choose_asset(r)['id'],5)
 def test_asset_ambiguous_fails(self):
  r=release('v3.7.9',asset=[])
  with self.assertRaises(RuntimeError):choose_asset(r)
 def test_prerelease_only_fails(self):
  with self.assertRaises(RuntimeError):choose_release([release('v1.3.0-beta'),release('v1.4.0',True)])
 def test_reject_malicious_asset_url(self):
  r=release('v3.7.9',asset=[{'id':5,'name':'Sandboxie-Plus-x64-v3.7.9.exe','size':10000000,'browser_download_url':'https://untrusted.example/a.exe'}])
  with self.assertRaises(RuntimeError):choose_asset(r)
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
