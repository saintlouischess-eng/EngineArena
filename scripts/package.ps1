$ErrorActionPreference = 'Stop'
$taskSourceRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskSourceRoot
New-Item -ItemType Directory -Path release\EngineArena\worker -Force | Out-Null
Copy-Item -Path dist\ArenaWorker\* -Destination release\EngineArena\worker -Recurse -Force
Copy-Item -LiteralPath README.md,requirements.txt -Destination release\EngineArena -Force
New-Item -ItemType Directory -Path release\EngineArena\docs -Force | Out-Null
Copy-Item -Path docs\* -Destination release\EngineArena\docs -Recurse -Force
New-Item -ItemType Directory -Path release\EngineArena\Validation -Force | Out-Null
foreach ($evidence in @('tester-preview-acceptance.xml','tester-math-audit.json','tester-pool-audit.json','tester-backup-report.json','tester-packaged-report.json','tester-ui-report.json','fastest-clock-acceptance.xml','fastest-clock-report.json','cpu-sensors-acceptance.xml','cpu-sensors-report.json','cpu-sensors-pipe-report.json','cpu-sensors-dependency-audit.json','hardware-acceptance.xml','hardware-report.json','results-controls-acceptance.xml','results-controls-report.json','results-controls-scale.json','pgn-export-acceptance.xml','pgn-export-report.json','pgn-export-scale.json','pgn-user-sample-report.json')) {
    $evidencePath = Join-Path 'test-output' $evidence
    if (Test-Path -LiteralPath $evidencePath) { Copy-Item -LiteralPath $evidencePath -Destination release\EngineArena\Validation -Force }
}
foreach ($evidence in @('opening-eval-acceptance.xml','opening-eval-report.json','acceptance.xml','graph-load-summary.json','validation-hardware.json','statistics-validation.json','statistics-sprt-simulation.json','ratings-validation.json','ponder-report.json','tablebase-edge-report.json','swiss-large-report.json','conditions-ui-report.json','failure-ui-report.json','python-audit.json','nuget-audit.json','packaged-report.json','packaged-json-ui-report.json','portable-crash-report.json','portable-crash-prior-report.json','history-scale-before.json','history-scale-after.json','history-live-report.json','history-recovery-report.json','controls-report.json','candidate-ui-report.json','portable-runtime-report.json','focus-font-report.json','clocks-deletion-report.json','deletion-scale-report.json','polish-report.json','polish-packaged-report.json','focus-search-report.json','live-boards-report.json')) {
    $evidencePath = Join-Path 'test-output' $evidence
    if (Test-Path -LiteralPath $evidencePath) { Copy-Item -LiteralPath $evidencePath -Destination release\EngineArena\Validation -Force }
}
New-Item -ItemType Directory -Path release\EngineArena\ThirdParty\python-chess -Force | Out-Null
Copy-Item -Path .venv\Lib\site-packages\chess\*.py -Destination release\EngineArena\ThirdParty\python-chess -Force
Copy-Item -Path .venv\Lib\site-packages\chess-1.11.2.dist-info\licenses\* -Destination release\EngineArena\ThirdParty\python-chess -Force
foreach ($metadata in Get-ChildItem -Path .venv\Lib\site-packages\*.dist-info -Directory) {
    $noticeTarget = Join-Path 'release\EngineArena\ThirdParty\PythonPackages' $metadata.Name
    New-Item -ItemType Directory -Path $noticeTarget -Force | Out-Null
    foreach ($notice in Get-ChildItem -LiteralPath $metadata.FullName -File | Where-Object { $_.Name -match '^(METADATA|LICENSE.*|COPYING.*)$' }) {
        Copy-Item -LiteralPath $notice.FullName -Destination $noticeTarget -Force
    }
    $licenseDirectory = Join-Path $metadata.FullName 'licenses'
    if (Test-Path -LiteralPath $licenseDirectory) { Copy-Item -LiteralPath $licenseDirectory -Destination $noticeTarget -Recurse -Force }
}
New-Item -ItemType Directory -Path release\EngineArena\ThirdParty\LibreHardwareMonitor -Force | Out-Null
Copy-Item -Path vendor\LibreHardwareMonitor\* -Destination release\EngineArena\ThirdParty\LibreHardwareMonitor -Force
$sourceFiles = & rg --files arena desktop sensors ui scripts tests installer
$sourceFiles += @('worker.py','README.md','pytest.ini','requirements.txt','requirements-dev.txt','requirements.lock.txt','requirements-statistics.txt')
foreach ($source in $sourceFiles) {
    $sourceTarget = Join-Path 'release\EngineArena\Source' $source
    New-Item -ItemType Directory -Path (Split-Path -Parent $sourceTarget) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $sourceTarget -Force
}
Compress-Archive -Path release\EngineArena\* -DestinationPath release\EngineArena-win-x64.zip -Force
Write-Output 'Portable output: release\EngineArena\EngineArena.exe'

