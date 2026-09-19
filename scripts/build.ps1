param([switch]$SkipTests)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
if (-not $SkipTests) {
    New-Item -ItemType Directory -Path test-output -Force | Out-Null
    & .\.venv\Scripts\python.exe -m pytest tests --basetemp test-output\pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Acceptance tests failed' }
}
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --name ArenaWorker --add-data 'ui;ui' worker.py
if ($LASTEXITCODE -ne 0) { throw 'Worker packaging failed' }
$taskReleaseTarget = [System.IO.Path]::GetFullPath((Join-Path $root 'release\EngineArena'))
$taskExpectedRelease = [System.IO.Path]::GetFullPath($root).TrimEnd('\') + '\release\EngineArena'
if ($taskReleaseTarget -ne $taskExpectedRelease) { throw 'Unexpected release output path' }
if (Test-Path -LiteralPath $taskReleaseTarget) { Remove-Item -LiteralPath $taskReleaseTarget -Recurse -Force }
& dotnet publish desktop\EngineArena.csproj -c Release -r win-x64 --self-contained true -p:PublishSingleFile=false -o $taskReleaseTarget
if ($LASTEXITCODE -ne 0) { throw 'Desktop publishing failed' }
& dotnet publish sensors\ArenaSensors.csproj -c Release -r win-x64 --self-contained true -o $taskReleaseTarget
if ($LASTEXITCODE -ne 0) { throw 'CPU sensor reader publishing failed' }
& .\scripts\package.ps1
