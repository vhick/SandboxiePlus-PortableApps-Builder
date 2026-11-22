# Windows-only; obtains unmodified upstream installer, verifies it and invokes upstream portable extraction.
param([string]$Resolved='work/resolved.json',[string]$Output='work/upstream')
$ErrorActionPreference='Stop'; Set-StrictMode -Version Latest
$r=Get-Content -Raw -LiteralPath $Resolved | ConvertFrom-Json
$base=[IO.Path]::GetFullPath($Output)
New-Item -ItemType Directory -Force -Path $base | Out-Null
$file=Join-Path $base $r.asset_name
$u=[uri]$r.asset_url
if ($u.Scheme -ne 'https' -or $u.Host -ne 'github.com' -or -not $u.AbsolutePath.StartsWith('/sandboxie-plus/Sandboxie/releases/download/')) {throw 'Untrusted upstream release URL'}
$downloaded=$false
for ($i=0;$i -lt 3 -and -not $downloaded;$i++) {
  try { Invoke-WebRequest -Uri $r.asset_url -OutFile $file -MaximumRedirection 5 -TimeoutSec 180; $downloaded=$true }
  catch { if ($i -eq 2) {throw}; Start-Sleep -Seconds ([int][math]::Pow(2,$i)) }
}
if ((Get-Item $file).Length -ne [long]$r.asset_size) {throw 'Upstream asset size changed during download'}
$sha=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
if ($r.asset_digest -and $r.asset_digest -ne "sha256:$sha") {throw 'GitHub-provided SHA256 digest mismatch'}
$sig=Get-AuthenticodeSignature -LiteralPath $file
if ($sig.Status -ne 'Valid') {throw "Official binary signature is not valid ($($sig.Status)); stop rather than bypass signature verification"}
# Record the actual signing identity, no fabricated publisher allowlist.
$record=@{sha256=$sha; signature_status=$sig.Status.ToString(); signer=$sig.SignerCertificate.Subject; issuer=$sig.SignerCertificate.Issuer; file=$r.asset_name}
$record | ConvertTo-Json | Set-Content (Join-Path $base 'integrity.json') -Encoding utf8
$portable=Join-Path $base 'Extracted'
if (Test-Path $portable) {throw 'Refusing to extract into nonempty output'}
New-Item -ItemType Directory -Force -Path $portable | Out-Null
$args=@('/PORTABLE=1','/CURRENTUSER','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',"/DIR=`"$portable`"")
$p=Start-Process -FilePath $file -ArgumentList $args -PassThru
try {
  if (-not $p.WaitForExit(180000)) {
    try {$p.Kill()}catch{}
    throw 'Upstream portable extraction exceeded three-minute timeout; no package published'
  }
  if ($p.ExitCode -ne 0) {throw "Upstream portable extraction failed: installer exit code $($p.ExitCode)"}
}finally {$p.Dispose()}
$required=@('SandMan.exe','Start.exe','SbieDrv.sys','SbieSvc.exe','KmdUtil.exe','SbieDll.dll','32\SbieDll.dll','Sandboxie.ini','Sandboxie-Plus.ini')
foreach ($rel in $required) {if (-not (Test-Path -LiteralPath (Join-Path $portable $rel) -PathType Leaf)){throw "Incomplete upstream portable extraction: missing $rel"}}
if (-not (Get-ChildItem -LiteralPath $portable -Filter 'Qt6Core.dll' -File)) {throw 'No Qt6 runtime; upstream asset layout changed'}
# Never launch SandMan/driver during CI: kernel-level functional testing belongs in a disposable VM.
Write-Host "Verified original upstream $($r.tag), SHA256 $sha, and portable extraction $portable"
