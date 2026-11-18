$ErrorActionPreference = 'Stop'

$root = $PSScriptRoot
$toolsRoot = Split-Path -Parent $root
$python = Join-Path $toolsRoot 'Python\python.exe'
$native = Join-Path $root 'make\native'
$mingw = Join-Path $toolsRoot 'MinGW\bin'
$core = Join-Path $root 'core'

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Portable Python was not found at '$python'. Expected the folder layout Tools\Python\python.exe and Tools\DWService\run-portable.ps1."
}
if (-not (Test-Path -LiteralPath (Join-Path $core 'agent.py') -PathType Leaf)) {
    throw "DWService core\agent.py was not found under '$root'."
}
if (-not (Test-Path -LiteralPath $native -PathType Container)) {
    throw "Native DLL directory was not found at '$native'."
}

$env:PATH = "$native;$mingw;$env:PATH"
$env:DWAS_DLL_DIRS = "$native;$mingw"
Set-Location -LiteralPath $core

$code = "import os, runpy; native=os.add_dll_directory(r'$native'); mingw=os.add_dll_directory(r'$mingw') if os.path.isdir(r'$mingw') else None; runpy.run_path(r'$core\agent.py', run_name='__main__')"
& $python -c $code
exit $LASTEXITCODE
