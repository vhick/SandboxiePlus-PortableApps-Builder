param([string]$Sandman='work/upstream/Extracted/SandMan.exe',[string]$Out='work/launcher/SandboxiePlusPortable.exe')
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
Add-Type -AssemblyName System.Drawing
$dest=[IO.Path]::GetFullPath($Out);New-Item -ItemType Directory -Force (Split-Path $dest) | Out-Null
$icon=Join-Path (Split-Path $dest) 'appicon.ico'
$i=[System.Drawing.Icon]::ExtractAssociatedIcon([IO.Path]::GetFullPath($Sandman))
if (-not $i) {throw 'Cannot extract legitimate upstream SandMan icon'}
try{$f=[IO.File]::Create($icon);try{$i.Save($f)}finally{$f.Dispose()}}finally{$i.Dispose()}
$compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $compiler)) {throw 'Windows .NET Framework C# compiler not found'}
$source=Join-Path $env:GITHUB_WORKSPACE 'launcher\SandboxiePlusPortable.cs'
& $compiler /nologo /target:winexe /platform:x64 "/out:$dest" "/win32icon:$icon" /r:System.Windows.Forms.dll /r:System.Web.Extensions.dll $source
if ($LASTEXITCODE -ne 0){throw 'Real executable launcher compilation failed'}
$ms=Get-Item $dest;if($ms.Length -lt 4096) {throw 'Unexpected launcher output size'}
$compilerInfo=@{compiler=$compiler; version=(Get-Item $compiler).VersionInfo.FileVersion; windows_version=[Environment]::OSVersion.VersionString; launcher_sha256=(Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant()}
$compilerInfo|ConvertTo-Json|Set-Content (Join-Path (Split-Path $dest) 'launcher-build.json') -Encoding utf8
Write-Host "Compiled real Windows PE launcher: $dest"
