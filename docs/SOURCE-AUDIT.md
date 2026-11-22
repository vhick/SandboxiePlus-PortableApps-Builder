# Upstream audit — Sandboxie Plus, November 22, 2026

## Current public release

The official upstream Releases listing showed **v1.19.1 / Classic 5.74.1** (November 21, 2026). The builder deliberately does not hardcode that release and resolves the next stable release from the official GitHub API. Supported target: **Plus x64** (not Classic/ARM64).

## Why an upstream binary acquisition architecture

The upstream project's `.github/workflows/main.yml` builds SbieRelease Win32 supporting DLLs and service, then x64 core and driver through MSBuild. Additional components use `SandboxiePlus/qmake_plus.cmd` (Qt qmake/Jom), `SandboxiePlus/SbieShell/SbieShell.sln` and `SandboxieTools/SandboxieTools.sln`. It pulls an upstream Qt toolchain with version and SHA recorded in `Installer/buildVariables.cmd`. This is complex and its kernel driver has user-mode/driver version coupling.

The Plus license `LICENSE.Plus` grants free redistribution of the original unmodified binaries. Public self-compiled Plus binary redistribution has extra requirements, including publishing all source changes and preserving name/authorship, with the upstream author's reserved right to prohibit unofficial binaries. This builder acquires official binary files and compiles only a wrapper, avoiding arbitrary driver patches.

## Portable settings and driver/service

From `Installer/Sandboxie-Plus.iss`: `/PORTABLE=1` enables the portable branch; `Uninstallable=not IsPortable`; the installer includes `Sandboxie.ini` and `Sandboxie-Plus.ini` in `{app}` only in portable mode. Its driver and service installation actions are `Check: not IsPortable`. Portable mode is not a promise that SandMan never elevates or installs driver/service during **first runtime use**. Driver and service are `SbieDrv.sys` and `SbieSvc.exe`, with `KmdUtil.exe` as the upstream maintenance utility.

The regular `Sandboxie.ini` lookup can prefer `C:\Windows\Sandboxie.ini`. The new launcher checks for conflict and refuses to silently override it. Upstream `%SbieHome%` can expand to the application directory for `FileRootPath`, allowing Data-relative *new* sandbox roots. Migration of old custom roots and existing config is separate.

## Real payload components

Inspect `Installer/copy_build.cmd` for upstream staging of core executables and modules. The selection contract requires `SandMan.exe`, `Start.exe`, `SbieDrv.sys`, `SbieSvc.exe`, `KmdUtil.exe`, `SbieDll.dll`, x86 supporting `32/SbieDll.dll`, plus Qt6Core and the two INI defaults. Every original `.exe/.dll/.sys` extracted is copied without modification and is byte-compared in static package validation. If an upstream file is renamed incompatibly, preflight fails rather than inventing a substitute.

The installer may contain optional ImDisk files and PDBs. This builder does not enable ImDisk installation. New stable releases may change bundled third-party libraries; acquisition inherits them from the official signed installer and records its hash rather than maintaining separate toolchain pins.

## Host ownership and risks

Kernel driver and Windows service registration are HOST state, not portable Data. Registry traces, driver installations, already-running sandboxed programs and explorer integrations cannot be generically rolled back without interfering with other installations. A Windows VM acceptance test is mandatory. Use upstream's UI/maintenance controls, not a custom driver installer script.

## Safety boundaries and deliberate shortcomings

The launcher captures the native root INI files and safe newly-created local data files/empty directories, but it cannot prove it has observed all possible AppData/ProgramData, host registry, global logs, elevated processes, or third-party sandbox add-on changes. Those unhandled cases must be manually audited; they must not be marketed as complete TraceGuard coverage. Sandbox file roots **explicitly** set elsewhere are not captured into Data. No automatic upgrades should be considered production safe without testing Windows service behavior, sandbox contents, reset and cleanup.

## References

- https://github.com/sandboxie-plus/Sandboxie/releases/tag/v1.19.1
- https://raw.githubusercontent.com/sandboxie-plus/Sandboxie/master/Installer/Sandboxie-Plus.iss
- https://raw.githubusercontent.com/sandboxie-plus/Sandboxie/master/Installer/copy_build.cmd
- https://raw.githubusercontent.com/sandboxie-plus/Sandboxie/master/Installer/buildVariables.cmd
- https://raw.githubusercontent.com/sandboxie-plus/Sandboxie/master/AGENTS.md
- https://raw.githubusercontent.com/sandboxie-plus/Sandboxie/master/LICENSE.Plus
- https://sandboxie-plus.github.io/sandboxie-docs/Content/SandboxieIni/
- https://sandboxie-plus.github.io/sandboxie-docs/Content/FileRootPath/
