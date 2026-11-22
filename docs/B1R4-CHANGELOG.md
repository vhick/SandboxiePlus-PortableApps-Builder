# b1r4 — authenticated release-guard correction

## Source evidence

- Uploaded GitHub Actions archive: `logs_121833446342.zip`, step 5 succeeded (`v1.19.1`, asset and upstream portable-mode license verification). Step 6 printed `Expected publisher tag: portable-v1.19.1-b1r3` and exited 1 before downloading the official binary.
- Root cause: `gh release view` reports exit code 1 for a non-existent tag, which is expected for a first build, but was not handled safely in the PowerShell workflow.
- External documentation: https://cli.github.com/manual/gh_help_exit-codes and https://docs.github.com/en/rest/releases/releases

## Fix

- New `scripts/check-existing.py` checks GitHub's authenticated REST release-by-tag endpoint.
- HTTP 404 permits the first build only after separately verifying access to the repository. HTTP 401, 403, 5xx and bad response data block instead of silently assuming missing release.
- Existing completed releases with one ZIP and one `.paf.exe` are skipped; incomplete/draft versions require manual review.
- Force rebuild can generate an unpublished candidate but cannot overwrite an existing release tag.
- Workflow now uses Python exit status and `GITHUB_OUTPUT` without triggering on an expected absence. Shared action pins remain unchanged.
- Bumped builder revision to `b1r4` consistently (workflow packager/release names, config and documents); known-good remains unverified.

## Tests

- 27 unchanged regression cases retained.
- 12 new mock-API release guard cases.
- Total: 39 passing offline tests in a non-Windows container.
- No claim of a complete Windows GitHub Actions build or driver/runtime acceptance. Re-run build with `publish=false`.
