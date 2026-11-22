# Actual validation record — initial kit

**Executed in current Linux file-generation environment:**

- Public upstream release, license, source installer, CI, and both pinned `action.yml` contracts inspected via web sources.
- `python -m unittest discover -s tests -v`: **11 tests passed** (stable numeric version ordering; prerelease exclusion; changed release asset version/name; ambiguous/malicious asset rejection; unexpected upstream INI failure; version/relocated extraction fixture; ZIP traversal and duplicate filename rejection; nested empty-directory ZIP preservation).
- Python parsing and the three GitHub workflow YAML files passed local syntax parsing. Metadata targets current PortableApps.com Format 3.9 (source specification). GitHub runtime compatibility is not established until GitHub Actions validates and executes it.

**Not executed, and must NOT be reported as passed:**

- Live GitHub API run from the built kit; official binary download or Authenticode verification; upstream Inno `/PORTABLE=1` extraction; C# compilation on Windows; actual Windows PE runtime startup; shared installer generation and upgrade behavior on Sandboxie; publisher dry-run and release creation; service/driver loading and unloading; sandboxed task execution; runtime new-file TraceGuard and crash recovery; manual driver-safe rollback and system trace checks.

**No functional Sandboxie executable, `.paf.exe`, or full application ZIP was produced in this environment.** The downloadable ZIP is a *builder source kit*. The actual applications are assembled by GitHub Actions after the user installs the builder.

**Known-good ledger:** `config/known-good.json` is intentionally unverified/null. Update this record only after a real build plus the Windows acceptance checklist; do not claim any current release is certified.

**Security/provenance boundaries:** GitHub release asset hash is recorded; an API `digest` is required to match when present, and Windows Authenticode must be valid. If GitHub does not supply a digest, this is authenticity based on the official release endpoint plus a valid signature, not independent proof that binary corresponds byte-for-byte to public source. All kernel code is upstream and unmodified.
