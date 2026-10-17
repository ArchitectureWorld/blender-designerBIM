# Usage: .\scripts\run_blender_tests.ps1 -BlenderExe 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
param([Parameter(Mandatory=$true)][string]$BlenderExe)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $BlenderExe -PathType Leaf)) { throw 'Blender executable not found' }
$Root = Split-Path -Parent $PSScriptRoot
$OutputDir = Join-Path $Root 'reports\blender-runtime'
& $BlenderExe --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot 'blender_smoke_test.py') -- $OutputDir
if ($LASTEXITCODE -ne 0) { throw "Blender runtime test failed (exit $LASTEXITCODE); see $OutputDir" }
Get-Content -LiteralPath (Join-Path $OutputDir 'runtime-result.json')
