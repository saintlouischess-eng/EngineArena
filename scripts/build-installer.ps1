param([string]$Compiler = '', [switch]$SkipPortableBuild)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$pins = Get-Content -LiteralPath installer\prerequisites.json -Raw | ConvertFrom-Json

function Get-VerifiedInstaller($spec, [string]$path) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $path) -Force | Out-Null
    if (-not (Test-Path -LiteralPath $path)) {
        Invoke-WebRequest -Uri $spec.url -OutFile $path -UseBasicParsing
    }
    $digest = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower()
    $signature = Get-AuthenticodeSignature -LiteralPath $path
    if ($digest -ne $spec.sha256 -or $signature.Status -ne 'Valid' -or
        $signature.SignerCertificate.Subject -notlike ('*'+$spec.signer+'*')) {
        throw "Prerequisite verification failed: $path. Review the upstream release before changing any pin."
    }
}

Get-VerifiedInstaller $pins.webview2 'optional-components\WebView2\MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
Get-VerifiedInstaller $pins.pawnio 'optional-components\PawnIO\PawnIO_setup.exe'
if (-not $Compiler) { $Compiler = Join-Path $taskRoot 'build\installer-tools\inno\ISCC.exe' }
if (-not (Test-Path -LiteralPath $Compiler)) { throw 'Install the pinned Inno Setup 6.7.3 compiler or pass -Compiler with its ISCC.exe path. See docs/BUILDING.md.' }
if (-not $SkipPortableBuild) {
    & scripts\build.ps1
    if ($LASTEXITCODE -ne 0) { throw 'Portable build failed' }
}

# Setup is x86 even though the application is x64. Resolve the loader from
# the restored SDK package instead of assuming a particular NuGet cache path.
$assets = Get-Content -LiteralPath desktop\obj\project.assets.json -Raw | ConvertFrom-Json
$sdk = @($assets.libraries.PSObject.Properties.Name | Where-Object { $_ -like 'Microsoft.Web.WebView2/*' })
if ($sdk.Count -ne 1) { throw 'Could not identify the restored WebView2 SDK' }
$probe = $null
foreach ($cache in $assets.packageFolders.PSObject.Properties.Name) {
    $candidate = Join-Path $cache ($sdk[0].ToLower()+'/runtimes/win-x86/native/WebView2Loader.dll')
    if (Test-Path -LiteralPath $candidate) { $probe = $candidate; break }
}
if (-not $probe) { throw 'WebView2 x86 setup loader missing; restore/build the desktop project first' }
New-Item -ItemType Directory -Path build\installer-tools -Force | Out-Null
Copy-Item -LiteralPath $probe -Destination build\installer-tools\ArenaWebViewProbe.dll -Force

$payload = [IO.Path]::GetFullPath((Join-Path $taskRoot 'build\installer-payload'))
$expectedPayload = [IO.Path]::GetFullPath($taskRoot).TrimEnd('\')+'\build\installer-payload'
if ($payload -ne $expectedPayload) { throw 'Unexpected installer payload directory' }
if (Test-Path -LiteralPath $payload) { Remove-Item -LiteralPath $payload -Recurse -Force }
New-Item -ItemType Directory -Path $payload -Force | Out-Null
foreach ($item in Get-ChildItem -LiteralPath release\EngineArena) {
    if ($item.Name -notin @('Source','Validation','docs','README.md')) {
        Copy-Item -LiteralPath $item.FullName -Destination $payload -Recurse -Force
    }
}
foreach ($directory in @('docs','Optional','Source','ThirdParty\PawnIO','ThirdParty\InnoSetup')) {
    New-Item -ItemType Directory -Path (Join-Path $payload $directory) -Force | Out-Null
}
Copy-Item -LiteralPath LICENSE,NOTICE,README.md -Destination $payload -Force
Copy-Item -LiteralPath docs\BETA_TESTING.html,docs\BETA_TESTING.md,docs\BETA_VALIDATION.md,docs\ACCEPTANCE.md,docs\STATISTICS.md,docs\HARDWARE.md,docs\THIRD_PARTY.md,docs\BUILDING.md -Destination (Join-Path $payload 'docs') -Force
Copy-Item -LiteralPath optional-components\PawnIO\PawnIO_setup.exe -Destination (Join-Path $payload 'Optional') -Force
Copy-Item -Path vendor\PawnIO\* -Destination (Join-Path $payload 'ThirdParty\PawnIO') -Force
Copy-Item -LiteralPath vendor\InnoSetup\LICENSE.txt -Destination (Join-Path $payload 'ThirdParty\InnoSetup') -Force
foreach ($notices in @('DotNet','WebView2SDK','Python')) {
    Copy-Item -LiteralPath (Join-Path 'vendor' $notices) -Destination (Join-Path $payload 'ThirdParty') -Recurse -Force
}

# A curated, auditable source snapshot: no local databases, exports, media, logs or Git history.
$sourceFiles = @(& rg --files arena desktop sensors ui scripts tests installer vendor)
$sourceFiles += @('worker.py','README.md','LICENSE','NOTICE','.gitignore','pytest.ini','requirements.txt','requirements-dev.txt','requirements.lock.txt','requirements-statistics.txt')
foreach ($source in $sourceFiles) {
    $destination = Join-Path (Join-Path $payload 'Source') $source
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}
Copy-Item -LiteralPath (Join-Path $payload 'docs') -Destination (Join-Path $payload 'Source') -Recurse -Force
$inventory = foreach ($file in Get-ChildItem -LiteralPath $payload -Recurse -File) {
    [pscustomobject]@{path=$file.FullName.Substring($payload.Length+1).Replace('\','/'); bytes=$file.Length; sha256=(Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLower()}
}
$inventory | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $payload 'package-manifest.json') -Encoding UTF8
& $Compiler '/Qp' ('/DPayloadDir='+$payload) installer\EngineArena.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
$setup = Join-Path $taskRoot 'release\EngineArenaSetup-0.2.0-beta.2-win-x64.exe'
$hash = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLower()
Set-Content -LiteralPath ($setup+'.sha256') -Value ($hash+'  '+[IO.Path]::GetFileName($setup)) -Encoding ASCII
Write-Output "Single offline installer: $setup"
Write-Output "SHA-256: $hash"
