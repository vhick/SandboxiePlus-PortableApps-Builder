# Mandatory Windows VM acceptance (not performed in the build environment)

**Use a disposable, snapshot-backed Windows 10/11 x64 VM.** Never run Sandboxie's driver/service smoke tests on your production host or inside GitHub-hosted runners without explicit safety review. The upstream binary may need administrator consent to register a kernel driver. Back up all old settings before testing.

## Phase 1 — independent ZIP

1. Download the candidate workflow artifact and extract `SandboxiePlusPortable_..._Win64.zip`. Verify root launcher is a genuine `.exe` with the upstream icon and the menu entry appears.
2. Confirm `App/Sandboxie/SandMan.exe`, `SbieDrv.sys`, `SbieSvc.exe`, `KmdUtil.exe`, `32/SbieDll.dll` exist, and the `Data` folder is next to the launcher.
3. Launch `SandboxiePlusPortable.exe`. If already installed system Sandboxie exists, confirm it **refuses** and does not overwrite that installation. Test normal success only on a clean VM.
4. Allow legitimate upstream driver/service prompts only if you understand the implications. Verify driver loads and a sandboxed benign `notepad.exe` starts. **Do not test unknown malware.**
5. Create/change a sandbox setting, UI setting, a file in a test sandbox and an entirely empty nested directory `Data/Sandboxes/test/empty/inside`. Close all sandboxed processes and exit SandMan. Check Data/Config and TraceGuard logs. Relaunch and verify settings, test file and empty directories remain.
6. Create an app-owned test `App/Sandboxie/TestDiagnostics/one/two/` with empty nested directory plus `report.log`. Close and relaunch; verify `Data/TraceGuard/RecoveredPaths/TestDiagnostics/...` was preserved. Do not add executable files.
7. Move the *whole* portable folder to a different path or drive letter while closed; relaunch and test data and sandbox root again. A host service might retain the original binary path — use upstream maintenance to update only this installation's driver/service in the VM; never assume relocation is safe while services are running.
8. Force-close `SandMan.exe` in a controlled benign test, then close relevant child tasks. Relaunch. Verify the launcher handles the `session.active` record and retains earlier files in `Data/TraceGuard/Recovery`, without deleting either config copy.
9. Check `C:\Windows\Sandboxie.ini`, `%LOCALAPPDATA%`, `%PROGRAMDATA%`, `HKLM\SYSTEM\CurrentControlSet\Services\SbieDrv`, and `...\SbieSvc` to **record remaining host traces**. Portability does not mean no traces.
10. Check host driver/service teardown through the upstream user interface, not a custom command. Restore the VM snapshot afterward.

## Phase 2 — installer upgrade

11. Install the independent `.paf.exe` into a clean PortableApps location. Check that its origin is described as **independent custom NSIS**, not officially certified.
12. Modify `Data/Config`, create nested empty directories, test sandbox content and `Data/TraceGuard/Recovery` markers; close all sandboxed tasks and upstream service where appropriate.
13. Upgrade to a second application revision using the shared packager; assert Data files and empty trees survive, old App-only files are replaced, unknown user files outside `Data` are not silently destroyed, and no stale partial install is mislabeled complete.
14. Induce a benign failed installer run in the disposable VM and inspect `.__UPB_Stage`/`.__UPB_Backup` recovery if present. Never manually delete ambiguous recovery data.
15. Check rollback separately; a Sandboxie database/profile or driver change may prevent safe downgrade even when installer file rollback succeeds. Record the exact version combinations actually tested.

**Publication gate:** check every applicable item, keep an audit log/screenshot, and only then set `manual_vm_acceptance=true` for that exact upstream version + builder revision. If a required step fails, retain the last good published release and do not attest success.
