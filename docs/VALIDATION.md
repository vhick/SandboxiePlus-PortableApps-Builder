# Actual validation record — b1r3

## Confirmed in provided Windows GitHub Actions logs

- b1r2 (`logs_121828798049.zip`): checkout, Python setup and **19** offline tests succeeded. Preflight failed on an incorrect literal Inno Setup installer path expectation. The real application ZIP and PAF installer were **not built**.

## Executed offline for b1r3 in this environment

- `python -m unittest discover -s tests -v`: **27 passed**, including existing 19 checks and 8 additional upstream installer INI validation cases.
- `python -m compileall`: passes for the builder Python files.
- YAML load checks passed for all three workflow files.
- Complete builder ZIP archive and its member CRC checks: passed.
- Static check: workflow and compatibility revision are consistently `b1r3`.

## External upstream evidence

The official v1.19.1 `Installer/Sandboxie-Plus.iss` has the following `[Files]` entries, which are represented in local test fixtures:

```
Source: ".\Sandboxie.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist; Check: IsPortable
Source: ".\Sandboxie-Plus.ini"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist; Check: IsPortable
```

Source: https://github.com/sandboxie-plus/Sandboxie/blob/v1.19.1/Installer/Sandboxie-Plus.iss

## Not executed

- Full live resolver with GitHub token or source retrieval at the exact tag
- Official installer binary download and Authenticode verification
- Real Windows upstream `/PORTABLE=1` extraction
- Windows C# launcher compilation/execution
- Shared packager and publisher operations
- Windows kernel service and driver startup/shutdown tests
- TraceGuard filesystem, empty-directory, crash and downgrade acceptance tests on a real PC

`config/known-good.json` intentionally records NO verified production package. `b1r3` is only a builder candidate, not a certified portable release.
