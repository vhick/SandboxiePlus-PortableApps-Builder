# Sandboxie Plus PortableApps Builder Kit — b1r4 (release-guard reliability fix; Windows-test candidate)

> **Status: 39 offline regression tests passed; b1r4 has NOT completed a Windows GitHub Actions build or driver/runtime acceptance test.** The first real build may expose issues requiring correction. Do not treat this as a certified PortableApps.com package or a no-trace portable security sandbox.

This is an **independent GitHub repository builder**, not a fork of [`sandboxie-plus/Sandboxie`](https://github.com/sandboxie-plus/Sandboxie). It fetches a verified official **Plus x64 stable installer**, asks the **upstream Inno Setup installer itself** to extract in `/PORTABLE=1` mode on a disposable Windows GitHub runner, and adds a compiled, non-obfuscated Windows launcher, portable `Data`, and recovery functionality. It builds a ready-to-extract ZIP independently and delegates `.paf.exe` creation to your pinned universal package builder and releases to your pinned publisher.

**Why not rebuild Sandboxie's kernel driver?** The actual software's `LICENSE.Plus` permits redistribution of original unmodified binaries free of charge, but publicly distributing self-compiled Plus binaries has additional terms. Compiling kernel code also creates driver-signing and security risks. This builder deliberately uses the original installer asset and verifies its Windows Authenticode signature, its official GitHub release URL, its byte count and its SHA-256 if GitHub supplies an asset digest. It records the observed SHA-256 even if an upstream published digest is not available. The upstream author still controls commercial use and support certificates.

## b1r4 reliability correction — new releases must not fail the build

The real b1r3 Actions run `logs_121833446342.zip` resolved official Plus `v1.19.1`, inspected its licensing and Inno portable configuration successfully, then failed in the *next* step. The old `gh release view <tag>` check exited with status 1 because a brand-new publisher tag did not yet exist. Redirecting CLI output was not sufficient to prevent the PowerShell job from stopping.

b1r4 uses `scripts/check-existing.py` and the authenticated GitHub REST API instead. For an absent tag (HTTP 404), it verifies that the token can access the *current builder repository* and then writes `skip=false` to `GITHUB_OUTPUT`. An existing, complete release with both a ZIP and a PAF-style EXE is skipped unless a candidate-only force rebuild is requested. Permission failures (401/403), server errors, inaccessible repositories, unexpected tags, incomplete releases, drafts, and attempts to overwrite an existing published release fail with clear diagnostics. `force_rebuild=true` with `publish=true` cannot overwrite an existing release tag.

The test count is **39**: 27 existing tests plus 12 new isolated GitHub release-guard tests. This fix addresses the exact b1r3 log failure, but **does not claim installer extraction, C# compilation, shared packager execution or runtime acceptance have passed yet**.

## Special Sandboxie limitations — read first

Sandboxie is not fully install-free: **SbieDrv.sys kernel driver and SbieSvc service require administrator-level host registration to actually run the sandbox.** Upstream SandMan manages these components; the new launcher never installs, stops, or removes system services or drivers by itself. Host traces may remain. A host's existing `C:\Windows\Sandboxie.ini` takes precedence over a local config, and an existing service using another installation will conflict; the launcher **refuses to start** in these cases rather than modify unrelated host state. Never run two different Sandboxie installations concurrently.

The default sandbox file root is `%SbieHome%\..\..\Data\Sandboxes\%USER%\%SANDBOX%`, corresponding to `Data\Sandboxes` relative to `App\Sandboxie`. This is based on upstream's documented `%SbieHome%` substitution. Do not move an existing custom sandbox merely by changing this setting. Do not assume every sandbox or add-on installed to a custom external directory will be captured into `Data`. Only project-owned/recognized local state is monitored.

The bundled launcher captures the two root `.ini` settings before closing, recovers interrupted sessions from local settings on next start, preserves known safe newly created data files under App/Sandboxie, and captures newly created empty nested directories. Sandbox contents are stored **directly** in `Data\Sandboxes`, so those files and empty directories need no post-run move. For unknown or executable runtime files, the launcher writes a **MANUAL REVIEW** record rather than blindly moving or executing them. It cannot monitor arbitrary elevated child processes with certainty, and does not claim to restore all Windows service or registry traces.

## Beginner setup with GitHub Desktop

1. Create a new empty repository in **GitHub Desktop → File → New repository**, e.g. `Sandboxie-Plus-PortableApps-Builder`. Do not fork the upstream Sandboxie repo.
2. Choose **public** or **private** based on who should receive your releases. Public GitHub Releases are public; private GitHub Releases remain private to authorized users. Never publish code or packages to a public repo if you intend the package to stay private.
3. Extract the **builder kit ZIP** from this conversation. Copy **all its contents**, including the hidden `.github` folder, directly into the new repository folder. The repository root should contain `README.md`, `scripts`, `launcher`, `config`, `tests` and `.github`.
4. GitHub Desktop → **Changes** → type the commit summary `Fix missing-release guard in Windows workflow (b1r4)` → **Commit to main** → **Publish repository** or **Push origin**.
5. On github.com open your own builder repository → **Actions** → enable workflows if GitHub asks.
6. Select **Sandboxie Plus - PortableApps ZIP and shared installer** → **Run workflow**. Leave `upstream_tag` blank for latest supported stable. Leave `installer_engine=custom-nsis`. For the first run, keep `publish=false` and `manual_vm_acceptance=false`. Run it.
7. On the completed run, open its **Artifacts** area → download the short-lived **CANDIDATE-VM-TEST** archive (two-day retention). It contains the ZIP and an independently generated `.paf.exe` installer if the build passed.
8. Test in an isolated, disposable Windows VM using the acceptance checklist in `docs/WINDOWS-ACCEPTANCE.md`. An administrator will be necessary for the driver/service; never run these tests on a production PC first.
9. **Only after successfully testing the same upstream version and builder revision**, rerun with its exact `upstream_tag`, `publish=true`, and `manual_vm_acceptance=true`. This attests that you performed those tests; the workflow cannot verify your attestation. **GitHub → your repository → Releases** will then contain both packages and `SHA256SUMS.txt`.
10. Extract the ZIP into a folder under `PortableApps` and use `SandboxiePlusPortable.exe` from PortableApps Menu. Alternatively, use the **independent** PAF-style installer. Do not interpret `.paf.exe` to mean official PortableApps.com certification.
11. Before upgrading, stop all running sandboxed processes, close SandMan, ensure the driver/service is not actively using the old path, back up `Data`, and use the new independent installer. Your `Data` must be preserved. A user-chosen custom sandbox folder outside `Data` needs a separate backup.
12. For a new stable upstream release, repeat step 6. It dynamically resolves versions and source dependencies *for the official-binary path*. If the source license, installer portable mode, signature, or payload layout changes materially, it fails closed and you must inspect the diagnosis before changing the builder.

## Workflows

| Workflow | Purpose | Releases by default? |
|---|---|---|
| `build-portableapps.yml` | Stable upstream resolver, trusted official installer extraction, compiled launcher, PortableApps ZIP, shared packager, optional publisher | No; manual VM attestation required |
| `repackage-only.yml` | Rebuild an installer from a **previously published and SHA256-verified** ZIP in this same repository, no upstream recompile/extraction | No |
| `maintenance-check.yml` | Check latest stable, source-level portable contract, license and availability of pinned shared action metadata | Never |

**Packaging-only:** Actions → **Repackage a validated release ZIP** → supply exact `source_release_tag`, exact ZIP asset filename, and a **new** `new_release_tag` beginning `portable-`. Leave `publish=false` for the first trial, then test and opt in to publish. It verifies the original SHA256SUMS.txt and ZIP before calling the shared packager. It will never overwrite an existing release tag.

**Experimental official installer engine:** `installer_engine=official` needs both the genuine official PortableApps Installer distribution URL and the vendor's independently verified SHA-256; otherwise fail safely. Default remains `custom-nsis`. The official engine's unattended success is unverified; don't use it for routine builds.

## Adaptability model and known-good policy

* Version discovery uses the official GitHub API, compares semantic versions numerically rather than by publication time, skips prereleases/drafts, filters Classic-only releases by requiring official Plus-x64 asset identity **before** comparing versions, and uses a strictly selected official Plus-x64 Inno Setup asset.
* Before running the installer, the resolver obtains its exact tag commit and checks `LICENSE.Plus` and `Installer/Sandboxie-Plus.iss` at that commit for the portable license and `IsPortable` safeguards. The installer audit interprets `[Files]` `Source`, `DestDir`, `Check` and `Flags` independently, rather than demanding a nonexistent combined `{app}\Sandboxie-Plus.ini` text literal. A change to the checked portable semantics fails closed for review.
* The upstream original Inno installer bundles the required Qt runtime, compiler output, driver and service: no unrelated Node/Rust/Go environments and no fragile forced dependency upgrades. This avoids drift in source toolchains, but means the builder relies on upstream continuing to distribute signed official installers with compatible portable flags.
* Builder runtime uses built-in Windows .NET Framework compiler for its own launcher; Windows SDK and WDK builds are **not** performed. The official release version, commit, installer SHA-256, signer identity, original binary identities, and launcher/compiler provenance are recorded inside each ZIP under `Other/Source`.
* The action versions are **intentionally pinned** to `vhick/Portable-Package-Builder@v1.0.0` and `vhick/portable-release-publisher@v1.1.1`. Maintenance checks do not silently upgrade them.
* New ZIP versions are versioned as `SandboxiePlusPortable_X.Y.Z_b1r4_Win64.zip`. Existing `portable-vX.Y.Z-b1r4` Releases are never overwritten or silently republished. `config/known-good.json` deliberately has no claimed working build before Windows acceptance. Successful release assets serve as immutable records for reproduction/rollback.
* Source layouts, asset names, or storage changes outside compatible evidence are treated as **incompatibility**, not auto-patched. If an upstream version fails, the old release remains untouched.
* GitHub Windows 2022 hosted runners and built-in .NET Framework compiler are baseline dependencies. If Microsoft removes them or changes support incompatibly, a reviewed builder revision is needed; no guaranteed arbitrary-future self-repair is possible.

## Installer/packaging and data boundaries

- `App/Sandboxie` contains original upstream extracted files; `App/DefaultData/Config` holds new-install defaults. AppInfo metadata targets PortableApps.com Format 3.9, but this independent package is not officially certified. At runtime, SandMan requires the two settings files adjacent to itself. The launcher copies them from/to `Data/Config` with recovery snapshots rather than leaving settings unprotected only under managed `App`.
- `Data/Sandboxes` is the new default for sandbox file trees. Existing external sandbox paths must be migrated through upstream procedures, not through this builder.
- `Data/TraceGuard/session.active` marks an interrupted launch. On the next launch the launcher preserves in-place config and previous saved revisions; `events.log`, recovered paths and a sandbox directory tree manifest are retained.
- Host driver registrations, access controls, service state, kernel driver loading, temporary files, system logs, and sandboxed child process changes are not fully reversible by a generic launcher.
- Universal Package Builder owns installer upgrade/rollback of `App`/`Other`/launcher. It preserves `Data` but can replace user-added files placed inside `App`, so user changes should reside in `Data`.
- Releasing both formats requires passing static validation, PE verification and SHA checks. The **actual Windows sandbox launch/service behavior is operator-attested, not CI-verified**; do not publish unless a disposable VM test has passed.
- All `.paf.exe` installers in this project are independent community installers unless explicitly using and successfully verifying the experimental official engine.

## Troubleshooting

- **No signed asset:** Stop. Inspect official upstream release and check signature. Never disable signature validation to force a build.
- **No matching Plus x64 release asset:** Upstream naming/architecture changed, or release not supported. Review `config/compatibility.json` and actual release metadata before changing patterns.
- **License/installer source check failed:** Upstream distribution terms or portable execution changed. Do not strip safeguards.
- **SandMan missing after extraction:** The upstream installer changed payload layout or portable mode; update only after a manual source audit.
- **Already installed Sandboxie service / C:\Windows\Sandboxie.ini:** Don't use multiple Sandboxie installations. Back up settings and follow upstream's official migration/cleanup procedure manually.
- **User data missing:** Do not rerun installer over unknown folders. Inspect `Data/Config`, `Data/TraceGuard`, `App/Sandboxie`, and external sandbox paths. Never delete backup/manifest folders blindly.
- **Publishing failed after packages were built:** Existing GitHub releases are preserved. Check publisher dry-run errors, permissions, tag uniqueness and repository visibility. A diagnostic candidate ZIP is not a validated production release.
- **Unexpected runtime binary/add-on:** Check `Data/TraceGuard/events.log` for `MANUAL REVIEW`. Do not blindly restore unknown executables.

**Source references:** [Upstream project](https://github.com/sandboxie-plus/Sandboxie), [upstream Plus license](https://github.com/sandboxie-plus/Sandboxie/blob/master/LICENSE.Plus), [upstream installer](https://github.com/sandboxie-plus/Sandboxie/blob/master/Installer/Sandboxie-Plus.iss), [upstream CI](https://github.com/sandboxie-plus/Sandboxie/blob/master/.github/workflows/main.yml), [file root documentation](https://sandboxie-plus.github.io/sandboxie-docs/Content/FileRootPath.html), [shared package builder](https://github.com/vhick/Portable-Package-Builder), [shared release publisher](https://github.com/vhick/portable-release-publisher).
