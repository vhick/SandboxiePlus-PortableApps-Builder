# Actual validation record — b1r4

## Confirmed from uploaded Windows GitHub Actions logs

- b1r3 log `logs_121833446342.zip` step 4: 27 offline tests passed on GitHub Actions Windows 2022 runner.
- Step 5: Sandboxie Plus v1.19.1 release detected; official asset, exact tag/commit, license and portable installer source contract were reported successfully.
- Step 6: duplicate release check printed `portable-v1.19.1-b1r3`, then workflow exited with status 1. Official installer download and packaging were never reached.
- b1r4 addresses the Step 6 logic, not the unexecuted installer or kernel driver behavior.

## Executed for b1r4 in this environment

- `python -m unittest discover -s tests -q`: **39 tests passed** (27 earlier plus 12 API response/permissions/force/asset/output-contract checks).
- Python syntax/bytecode compilation and YAML structural parsing: see local build validation.
- ZIP integrity and extraction test: see local build validation.

## Not executed / unverified

- Actual Windows Actions run of b1r4
- Official installer binary download, signature and `/PORTABLE=1` extraction
- Windows C# launcher compilation and execution
- Shared Portable Package Builder and Publisher run for b1r4
- Real sandbox driver/service launch, TraceGuard, portable data and upgrades

`config/known-good.json` intentionally records **NO VERIFIED WINDOWS BUILD**. b1r4 remains a test candidate, not a verified application package.
