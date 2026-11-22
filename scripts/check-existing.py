#!/usr/bin/env python3
"""Check immutable release status without failing when the tag is genuinely absent.

Uses authenticated GitHub REST API. 404 is considered "not released yet" ONLY
if this token can also read the expected repository. Any other API problem
is a blocking error; never claim a successful release or skip by guessing.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API_VERSION = '2022-11-28'
TAG_RE = re.compile(r'^portable-v[0-9]+\.[0-9]+\.[0-9]+-b[0-9]+r[0-9]+$')
REPO_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$')


def get_json(path, token, base='https://api.github.com', *, urlopen=urllib.request.urlopen):
    if not base.startswith('https://'):
        raise ValueError('GitHub API base must use HTTPS')
    req = urllib.request.Request(base.rstrip('/') + path, headers={
        'Accept': 'application/vnd.github+json',
        'Authorization': 'Bearer ' + token,
        'X-GitHub-Api-Version': API_VERSION,
        'User-Agent': 'SandboxiePlus-PortableApps-Builder',
    })
    try:
        with urlopen(req, timeout=25) as resp:
            value = json.load(resp)
            if not isinstance(value, dict):
                raise RuntimeError('GitHub API returned unexpected JSON response')
            return value
    except urllib.error.HTTPError:
        raise  # Caller distinguishes 404 from authentication and server errors.
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f'GitHub API is unavailable: {exc}') from exc


def inspect_release(repo, tag, token, *, get=get_json):
    """Return None for absent release, or one verified complete release object."""
    if not REPO_RE.fullmatch(repo):
        raise ValueError('Invalid GITHUB_REPOSITORY: expected owner/name')
    if not TAG_RE.fullmatch(tag):
        raise ValueError('Unsafe or unexpected portable release tag: ' + tag)
    if not token:
        raise ValueError('Missing GH_TOKEN; cannot verify release state')

    safe_tag = urllib.parse.quote(tag, safe='')
    prefix = '/repos/' + repo
    try:
        result = get(prefix + '/releases/tags/' + safe_tag, token)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise RuntimeError(
                f'Cannot determine existing release status: GitHub HTTP {exc.code}; '
                'check token permissions, rate limits and GitHub availability'
            ) from exc
        # A 404 can also conceal inaccessible private repos. Confirm access.
        try:
            metadata = get(prefix, token)
        except urllib.error.HTTPError as access_exc:
            raise RuntimeError(
                f'GitHub release query was 404 and repository access failed '
                f'(HTTP {access_exc.code}); not safe to assume tag is absent'
            ) from access_exc
        if metadata.get('full_name', '').casefold() != repo.casefold():
            raise RuntimeError('Could not independently verify the requested GitHub repository')
        return None

    if result.get('tag_name') != tag:
        raise RuntimeError('GitHub API returned a release with an unexpected tag')
    if result.get('draft', False):
        raise RuntimeError('Tag already has a draft release; review manually, do not overwrite')
    assets = result.get('assets')
    if not isinstance(assets, list):
        raise RuntimeError('Existing release asset list is missing or malformed')
    names = []
    for asset in assets:
        if not isinstance(asset, dict) or asset.get('state') != 'uploaded':
            raise RuntimeError('Existing release has an incomplete or unrecognized asset')
        name = asset.get('name')
        if not isinstance(name, str):
            raise RuntimeError('Existing release asset name is invalid')
        names.append(name)
    if len([n for n in names if n.lower().endswith('.zip')]) != 1 or \
       len([n for n in names if n.lower().endswith('.paf.exe')]) != 1:
        raise RuntimeError(
            f'Existing release {tag} has incomplete package assets: {names!r}; '
            'manual review required to preserve release integrity'
        )
    return result


def decide(repo, tag, token, force=False, publish=False, *, get=get_json):
    release = inspect_release(repo, tag, token, get=get)
    if release is None:
        return False, f'No existing release {tag}; proceed with first-time build.'
    if force and publish:
        raise RuntimeError(
            f'Release {tag} already exists. force_rebuild + publish cannot overwrite '
            'an existing release. Disable publish for a test run or advance package revision.'
        )
    if force:
        return False, (f'Release {tag} already exists, but force_rebuild=true and '
                       'publish=false; producing test candidate only.')
    return True, f'Existing complete release {tag} found; skipping duplicate build.'


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--tag', required=True)
    args = p.parse_args(argv)
    skip, message = decide(
        os.environ.get('GITHUB_REPOSITORY', ''), args.tag,
        os.environ.get('GH_TOKEN', ''),
        force=os.environ.get('FORCE_REBUILD', '').lower() == 'true',
        publish=os.environ.get('PUBLISH', '').lower() == 'true',
    )
    print(message)
    output = os.environ.get('GITHUB_OUTPUT')
    if not output:
        raise RuntimeError('Missing GITHUB_OUTPUT; cannot set job skip decision')
    with Path(output).open('a', encoding='utf-8', newline='\n') as f:
        f.write('skip=' + str(skip).lower() + '\n')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, urllib.error.HTTPError) as e:
        print('RELEASE GUARD FAILED: ' + str(e), file=sys.stderr)
        sys.exit(1)
