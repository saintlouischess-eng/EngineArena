param([string]$Data, [switch]$BuildOnly)
$ErrorActionPreference = 'Stop'
$taskSourceRoot = Split-Path -Parent $PSScriptRoot
$taskDevelopmentOutput = Join-Path $taskSourceRoot 'build\development'
$taskDesktopProject = Join-Path $taskSourceRoot 'desktop\EngineArena.csproj'
$taskSensorProject = Join-Path $taskSourceRoot 'sensors\ArenaSensors.csproj'

# Publish both components together. The desktop loads the current source worker/UI
# from the repository, without replacing the packaged release or installer.
foreach ($taskProject in @($taskDesktopProject, $taskSensorProject)) {
    & dotnet publish $taskProject -c Release -r win-x64 --self-contained false -o $taskDevelopmentOutput
    if ($LASTEXITCODE -ne 0) { throw "Development build failed: $taskProject" }
}
foreach ($taskRequired in @('EngineArena.exe', 'EngineArena.dll', 'ArenaSensors.exe', 'ArenaSensors.dll', 'ArenaSensors.deps.json', 'ArenaSensors.runtimeconfig.json', 'LibreHardwareMonitorLib.dll')) {
    if (-not (Test-Path -LiteralPath (Join-Path $taskDevelopmentOutput $taskRequired))) {
        throw "Development build is incomplete: $taskRequired"
    }
}
if (Test-Path -LiteralPath (Join-Path $taskDevelopmentOutput 'worker\ArenaWorker.exe')) {
    throw 'The development folder contains a packaged worker; use a separate folder for release builds.'
}
if ($BuildOnly) { Write-Output "Development build ready: $taskDevelopmentOutput"; return }
$taskLaunch = @{
    FilePath = Join-Path $taskDevelopmentOutput 'EngineArena.exe'
    WorkingDirectory = $taskSourceRoot
    PassThru = $true
}
if ($Data) {
    $taskDataPath = [System.IO.Path]::GetFullPath($Data)
    $taskLaunch.ArgumentList = @('--data', ('"' + ($taskDataPath -replace '(\\+)$', '$1$1') + '"'))
}
$taskProcess = Start-Process @taskLaunch
Write-Output "Started Engine Arena development build (PID $($taskProcess.Id))."
