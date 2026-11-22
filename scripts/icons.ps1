param([string]$Stage='work/SandboxiePlusPortable',[string]$ExtractedIcon='work/launcher/appicon.ico')
$ErrorActionPreference='Stop';Add-Type -AssemblyName System.Drawing
$info=Join-Path $Stage 'App/AppInfo';New-Item -ItemType Directory -Force $info | Out-Null
Copy-Item -LiteralPath $ExtractedIcon -Destination (Join-Path $info 'appicon.ico')
$ico=[System.Drawing.Icon]::new([IO.Path]::GetFullPath($ExtractedIcon))
try{
  foreach($size in @(16,32)) {
    $bitmap=New-Object System.Drawing.Bitmap($size,$size)
    try{$graphics=[System.Drawing.Graphics]::FromImage($bitmap);try{$graphics.DrawIcon($ico,([System.Drawing.Rectangle]::new(0,0,$size,$size)))}finally{$graphics.Dispose()};$bitmap.Save((Join-Path $info "appicon_$size.png"),[System.Drawing.Imaging.ImageFormat]::Png)}finally{$bitmap.Dispose()}
  }
}finally{$ico.Dispose()}
