"""Offline simulations for the GitHub release guard (no API token/network needed)."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('release_guard',ROOT/'scripts'/'check-existing.py')
rg=importlib.util.module_from_spec(spec)
spec.loader.exec_module(rg)
REPO='vhick/SandboxiePlus-PortableApps-Builder'
TAG='portable-v1.19.1-b1r4'


def http_error(code):
    return urllib.error.HTTPError('https://api.github.com/example',code,'fixture',{},io.BytesIO(b''))


def lookup_missing(path,token):
    if path.endswith('/releases/tags/'+TAG): raise http_error(404)
    if path == '/repos/'+REPO: return {'full_name':REPO}
    raise AssertionError('Unexpected URL '+path)


def release(assets=None):
    if assets is None:
        assets=[{'name':'SandboxiePlusPortable_1.19.1_b1r4_Win64.zip','state':'uploaded'},
                {'name':'SandboxiePlusPortable_1.19.1_b1r4_Win64.paf.exe','state':'uploaded'}]
    return {'tag_name':TAG,'draft':False,'assets':assets}

class ReleaseGuard(unittest.TestCase):
    def test_new_release_404_permitted_after_repo_access(self):
        self.assertIsNone(rg.inspect_release(REPO,TAG,'token',get=lookup_missing))
        self.assertFalse(rg.decide(REPO,TAG,'token',get=lookup_missing)[0])

    def test_existing_complete_release_skipped(self):
        self.assertTrue(rg.decide(REPO,TAG,'token',get=lambda path,t:release())[0])

    def test_existing_partial_release_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError,'incomplete package assets'):
            rg.decide(REPO,TAG,'token',get=lambda path,t:release([{'name':'only.zip','state':'uploaded'}]))

    def test_api_403_is_error_not_absent(self):
        with self.assertRaisesRegex(RuntimeError,'HTTP 403'):
            rg.inspect_release(REPO,TAG,'token',get=lambda path,t:(_ for _ in ()).throw(http_error(403)))

    def test_api_500_is_error_not_absent(self):
        with self.assertRaisesRegex(RuntimeError,'HTTP 500'):
            rg.inspect_release(REPO,TAG,'token',get=lambda path,t:(_ for _ in ()).throw(http_error(500)))

    def test_api_404_with_no_repository_access_is_error(self):
        def fake(path,t): raise http_error(404)
        with self.assertRaisesRegex(RuntimeError,'repository access failed'):
            rg.inspect_release(REPO,TAG,'token',get=fake)

    def test_existing_release_force_candidate_allowed(self):
        should_skip, message = rg.decide(REPO,TAG,'token',force=True,publish=False,get=lambda path,t:release())
        self.assertFalse(should_skip)
        self.assertIn('test candidate',message)

    def test_existing_release_force_publish_blocked(self):
        with self.assertRaisesRegex(RuntimeError,'cannot overwrite'):
            rg.decide(REPO,TAG,'token',force=True,publish=True,get=lambda path,t:release())

    def test_existing_draft_release_blocked(self):
        x=release();x['draft']=True
        with self.assertRaisesRegex(RuntimeError,'draft'):
            rg.inspect_release(REPO,TAG,'token',get=lambda path,t:x)

    def test_unexpected_release_tag_blocked(self):
        x=release();x['tag_name']='portable-v1.19.1-b1r2'
        with self.assertRaisesRegex(RuntimeError,'unexpected tag'):
            rg.inspect_release(REPO,TAG,'token',get=lambda path,t:x)

    def test_tag_and_repo_input_validations(self):
        with self.assertRaises(ValueError):rg.inspect_release(REPO,'bad tag','token',get=lookup_missing)
        with self.assertRaises(ValueError):rg.inspect_release('../other',TAG,'token',get=lookup_missing)
        with self.assertRaises(ValueError):rg.inspect_release(REPO,TAG,'',get=lookup_missing)

    def test_output_contract_on_windows_style_file(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'github-output.txt'
            with patch.dict(os.environ, {'GITHUB_REPOSITORY':REPO,'GH_TOKEN':'x',
                     'FORCE_REBUILD':'false','PUBLISH':'false','GITHUB_OUTPUT':str(out)}):
                with patch.object(rg, 'inspect_release', return_value=None):
                    self.assertEqual(rg.main(['--tag',TAG]),0)
            self.assertEqual(out.read_bytes(),b'skip=false\n')

if __name__=='__main__':unittest.main()
