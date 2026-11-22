# b1r3 — correct upstream Inno Setup portable config validation

## Evidence from user-provided GitHub Actions run

- Run: `logs_121828798049.zip`; preflight on 2026-11-22, `main` at commit `50d121dc289e3de2ebd2c5406452fa53c43d6603`.
- Step: **Resolve stable upstream release and audit upstream portable mode at its tag**.
- Error: `PREFLIGHT FAILED: Upstream portable installer compatibility assumptions changed: {app}\Sandboxie-Plus.ini`.
- Previous 19 offline tests completed; the upstream installer download/extraction and packaging were not attempted.

## Root cause

The old audit expected `{app}\Sandboxie-Plus.ini` as a literal substring of the upstream `Installer/Sandboxie-Plus.iss`. The official v1.19.1 script uses two Inno Setup fields on a file directive: `Source: ".\Sandboxie-Plus.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist; Check: IsPortable`. Because the literal concatenation never appears, the old audit had a false negative.

## Fix

`scripts/resolve.py` now parses Inno `[Files]` entries, requiring one safe installation instruction for each portable INI file. The exact source filename, destination directory, `Check: IsPortable`, and `onlyifdoesntexist` upgrade-protection flag are checked. Macros and unexpected storage paths fail with an actionable diagnostic instead of being accepted blindly. The normal upstream license and portable-mode gates remain enforced.

The fix is designed to accept compatible formatting and source path variations and intentionally reject changes to the INI filenames, destination, upgrade safety, or portable conditions.

## Results and remaining validation

- 27 offline Python regression tests passed locally, including eight new Inno source checks.
- Syntax checks for Python and three GitHub Actions YAML files passed locally.
- Live GitHub source download, extraction, PE launcher compilation, shared installer packaging, sandbox driver functionality and publication have not been verified by this revision yet.
- Shared packager remains `vhick/Portable-Package-Builder@v1.0.0`, shared publisher remains `vhick/portable-release-publisher@v1.1.1`.

Reference: https://github.com/sandboxie-plus/Sandboxie/blob/v1.19.1/Installer/Sandboxie-Plus.iss
