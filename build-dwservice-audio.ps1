$ErrorActionPreference = 'Stop'

$root = 'C:\Users\athom\Tools\DWService'
$mingwBin = 'C:\Users\athom\Tools\MinGW\bin'
$gpp = Join-Path $mingwBin 'g++.exe'
$objdump = Join-Path $mingwBin 'objdump.exe'
$nativeDir = Join-Path $root 'make\native'
$tmpLibDir = Join-Path $root 'make\tmp\lib_rtaudio'
$configPath = Join-Path $root 'core\config.json'
$workDir = Join-Path $env:TEMP 'dwservice-rtaudio-seh-build'
$archive = Join-Path $workDir 'rtaudio-5.1.0.zip'
$sourceZipUrl = 'https://github.com/thestk/rtaudio/archive/refs/tags/5.1.0.zip'

Write-Host 'DWService audio runtime repair' -ForegroundColor Cyan

if (-not (Test-Path $root)) { throw "DWService folder not found: $root" }
if (-not (Test-Path $gpp)) { throw "MinGW compiler not found: $gpp" }
if (-not (Test-Path $configPath)) { throw "DWService config not found: $configPath" }

New-Item -ItemType Directory -Force -Path $workDir | Out-Null
$sourceDir = Join-Path $workDir 'rtaudio-5.1.0'
if (Test-Path $sourceDir) { Remove-Item $sourceDir -Recurse -Force }
if (Test-Path $archive) { Remove-Item $archive -Force }

Write-Host 'Downloading official RtAudio 5.1.0 source...'
Invoke-WebRequest -Uri $sourceZipUrl -OutFile $archive -UseBasicParsing

Write-Host 'Extracting RtAudio source...'
Expand-Archive -Path $archive -DestinationPath $workDir -Force
$extracted = Get-ChildItem $workDir -Directory | Where-Object { Test-Path (Join-Path $_.FullName 'RtAudio.cpp') } | Select-Object -First 1
if (-not $extracted) { throw 'Could not locate RtAudio.cpp in the downloaded source archive.' }
$sourceDir = $extracted.FullName

$required = @('RtAudio.cpp', 'RtAudio.h', 'rtaudio_c.cpp', 'rtaudio_c.h')
foreach ($file in $required) {
    if (-not (Test-Path (Join-Path $sourceDir $file))) { throw "Required RtAudio source file missing: $file" }
}

$outFile = Join-Path $workDir 'librtaudio.dll'
$compileArgs = @(
    '-std=c++11',
    '-O2',
    '-shared',
    '-DRTAUDIO_EXPORT',
    '-D__WINDOWS_WASAPI__',
    '-D__WINDOWS_DS__',
    "-I$sourceDir",
    '-o', $outFile,
    (Join-Path $sourceDir 'RtAudio.cpp'),
    (Join-Path $sourceDir 'rtaudio_c.cpp'),
    '-lole32',
    '-lwinmm',
    '-luuid',
    '-lksuser',
    '-lmfplat',
    '-lmfuuid',
    '-lwmcodecdspuuid',
    '-ldsound',
    '-lcomdlg32',
    '-lsetupapi'
)

Write-Host 'Compiling RtAudio with the installed SEH MinGW toolchain...'
& $gpp @compileArgs
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $outFile)) {
    throw "RtAudio compilation failed (exit code $LASTEXITCODE). Existing DLLs and config were not changed."
}

if (Test-Path $objdump) {
    $imports = & $objdump -p $outFile | Out-String
    if ($imports -match 'libgcc_s_sjlj|_Unwind_SjLj') {
        throw 'The newly built DLL still imports the incompatible SJLJ runtime. Existing DLLs and config were not changed.'
    }
    if ($imports -notmatch 'libgcc_s_seh') {
        Write-Warning 'The new DLL does not show a dynamic SEH libgcc import. Continuing because static linkage may be in use.'
    }
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
foreach ($target in @((Join-Path $nativeDir 'librtaudio.dll'), (Join-Path $tmpLibDir 'librtaudio.dll'))) {
    if (-not (Test-Path (Split-Path $target -Parent))) { New-Item -ItemType Directory -Force -Path (Split-Path $target -Parent) | Out-Null }
    if (Test-Path $target) { Copy-Item $target "$target.before-seh-$stamp.bak" -Force }
    Copy-Item $outFile $target -Force
}

Write-Host 'Enabling DWService sound capture in config.json...'
$config = Get-Content $configPath -Raw | ConvertFrom-Json
$config.'desktop.sound_enable' = $true
$json = $config | ConvertTo-Json -Depth 30
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($configPath, $json, $utf8NoBom)

Write-Host ''
Write-Host 'SUCCESS: rebuilt RtAudio with the installed MinGW toolchain.' -ForegroundColor Green
Write-Host 'The old DLLs were backed up beside their originals.'
Write-Host 'Sound capture has been enabled in config.json.'
Write-Host 'Restart DWService with .\run-portable.ps1 and test a remote session.'
