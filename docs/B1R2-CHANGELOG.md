# b1r2 release resolver maintenance fix

Incident: `logs_121825961297.zip` (2026-11-22) failed during Step 5: resolver incorrectly selected Classic `v5.40.1`, which only had `SandboxieInstall32/64` assets.

## Changes
- Identify official Sandboxie Plus x64 installer assets **before** semantic comparison; never compare Plus 1.x to Classic 5.x.
- Keep strict validation of exactly one Plus-x64 installer, official GitHub origin and digest.
- Resolve manual stable tags via the official release-by-tag API endpoint instead of a page limit.
- Match upstream license preflight terms without dependence on text capitalization. Keep all required permission-language checks and fail-closed behavior.
- Add concrete Classic-versus-Plus and license regression tests.

## Limits
- This is an offline-tested Windows-build **candidate**, not a certified working portable application.
- All kernel driver and service behavior still requires a Windows VM acceptance test.
- Upstream license, installer source and signature are always validated during the real build. No signature bypass is added.
