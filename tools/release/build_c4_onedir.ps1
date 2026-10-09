[CmdletBinding()]
param(
    [string]$BuildRoot = (Join-Path $env:LOCALAPPDATA 'C4\v1.2-onedir-build'),
    [string]$OutputRoot = (Join-Path $env:LOCALAPPDATA 'C4\v1.2-onedir-output'),
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$spec = Join-Path $repo 'packaging\windows\v1.2_onedir.spec'
$lock = Join-Path $PSScriptRoot 'C4_ONEDIR_REQUIREMENTS-WIN64.lock'
$python = (& py -3.12 -c "import platform,sys; print(sys.executable); print(sys.version_info.major,sys.version_info.minor,sys.version_info.micro,platform.machine())").Trim().Split("`n")
if ($LASTEXITCODE -ne 0 -or $python.Count -lt 2 -or $python[1].Trim() -ne '3 12 10 AMD64') {
    throw 'Build requires CPython 3.12.10 x64 (AMD64); no alternate runtime is accepted.'
}
$basePython = $python[0].Trim()
$venv = Join-Path $BuildRoot 'venv'
$dist = Join-Path $OutputRoot 'dist'
$work = Join-Path $BuildRoot 'pyinstaller-work'
$log = Join-Path $BuildRoot 'build.log'
$inventory = Join-Path $OutputRoot 'PACKAGE_INVENTORY.json'
New-Item -ItemType Directory -Force -Path $BuildRoot,$OutputRoot | Out-Null

Push-Location $repo
try {
    & $basePython (Join-Path $repo 'tools\verify_v09_fallback_assets.py')
    if ($LASTEXITCODE -ne 0) { throw 'Frozen V0.9 asset verification failed.' }
    if (-not $SkipBuild) {
        if (Test-Path -LiteralPath $venv) { throw 'Use a fresh BuildRoot; existing environments are preserved.' }
        & $basePython -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated build venv.' }
        $venvPython = Join-Path $venv 'Scripts\python.exe'
        & $venvPython -m pip install --disable-pip-version-check --requirement $lock
        if ($LASTEXITCODE -ne 0) { throw 'Pinned dependency installation failed.' }
        & $venvPython -m pip check
        if ($LASTEXITCODE -ne 0) { throw 'Pinned build environment failed pip check.' }
        $env:C4_REPO_ROOT = $repo
        & $venvPython -m PyInstaller --clean --noconfirm --distpath $dist --workpath $work $spec *> $log
        if ($LASTEXITCODE -ne 0) { Get-Content -LiteralPath $log -Tail 100; throw 'PyInstaller build failed.' }
        Remove-Item Env:\C4_REPO_ROOT -ErrorAction SilentlyContinue
    }
    $package = Join-Path $dist '讲义生成器'
    $exe = Join-Path $package '讲义生成器.exe'
    if (-not (Test-Path -LiteralPath $exe)) { throw "Expected onedir executable is missing: $exe" }
    if (-not (Test-Path -LiteralPath (Join-Path $package '_internal'))) { throw 'PyInstaller _internal directory is missing.' }
    $versions = (& (Join-Path $venv 'Scripts\python.exe') -c "import sys,platform,flask,lxml,docx,PyInstaller; import importlib.metadata as m; print('\n'.join([sys.version.split()[0],platform.machine(),'Flask '+flask.__version__,'lxml '+lxml.__version__,'python-docx '+docx.__version__,'PyInstaller '+PyInstaller.__version__]))").Trim()
    $files = Get-ChildItem -LiteralPath $package -File -Recurse | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($package.Length + 1).Replace('\','/')
        [ordered]@{ path=$relative; size_bytes=$_.Length; sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant() }
    }
    $excluded = @($files | Where-Object { $_.path -match '(?i)(ocr_models|image_role_evidence|rapidocr|onnxruntime|opencv|/cv2/|/numpy[/.\-]|/shapely[/.\-]|/pyclipper/|\.onnx$)' -or $_.path -match '(^|/)(tests?|corpus|gold|\.git|__pycache__|\.pytest_cache|\.venv)(/|$)' -or $_.path -match '(^|/)(private|uat)(/|$)' })
    if ($excluded.Count) { throw ('Forbidden package content found: ' + (($excluded | ForEach-Object path) -join ', ')) }
    $required = @(
        '_internal/v1.2-xml-experiment/res/app/webapp/templates/index.html',
        '_internal/v1.2-xml-experiment/res/app/webapp/static/workspace.js',
        '_internal/v1.2-xml-experiment/res/app/webapp/static/workspace.css',
        '_internal/v1.2-xml-experiment/res/app/reviewed_studentizer/X008.json',
        '_internal/tools/stage2_baseline/run_baseline.py',
        '_internal/v1.1-stable/res/app/2025+1v1讲义模板(2).docx',
        '_internal/v1.1-stable/res/app/2025班课模板.docx'
    )
    $actualPaths = @($files | ForEach-Object path)
    foreach ($path in $required) { if ($path -notin $actualPaths) { throw "Required packaged resource missing: $path" } }
    $assetManifestPath = Join-Path $repo 'v1.2-xml-experiment\res\app\v09_fallback_runtime\ASSET_MANIFEST.json'
    $assetManifest = Get-Content -Raw -Encoding UTF8 $assetManifestPath | ConvertFrom-Json
    $packagedV09Root = Join-Path $package '_internal\v1.2-xml-experiment\res\app\v09_fallback_runtime'
    foreach ($asset in $assetManifest.assets) {
        $assetPath = Join-Path $packagedV09Root $asset.target
        if (-not (Test-Path -LiteralPath $assetPath)) { throw "Packaged frozen V0.9 asset missing: $($asset.target)" }
        $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $assetPath).Hash.ToLowerInvariant()
        if ($actualHash -ne $asset.sha256) { throw "Packaged frozen V0.9 asset changed: $($asset.target)" }
    }
    [long]$totalBytes = 0
    foreach ($file in $files) { $totalBytes += [long]$file.size_bytes }
    $canonical = ($files | ForEach-Object { '{0}`t{1}`t{2}' -f $_.path,$_.size_bytes,$_.sha256 }) -join "`n"
    # SHA256.HashData / Convert.ToHexString require .NET 5+; Windows PowerShell
    # 5.1 runs on .NET Framework 4.x, so compute the same digest with APIs that
    # exist there. Algorithm and output are unchanged.
    $treeSha = [Security.Cryptography.SHA256]::Create()
    $treeHash = -join ($treeSha.ComputeHash([Text.Encoding]::UTF8.GetBytes($canonical)) |
        ForEach-Object { $_.ToString('x2') })
    $summary = [ordered]@{
        package_name='讲义生成器 onedir'
        build_interpreter='CPython 3.12.10 x64 (Windows AMD64)'
        dependency_versions=$versions -split "`n"
        package_root=$package
        file_count=$files.Count
        total_bytes=$totalBytes
        package_tree_sha256=$treeHash
        v09_manifest_assets_verified=$assetManifest.assets.Count
        files=$files
    }
    $summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $inventory -Encoding UTF8
    Write-Output "PACKAGE=$package"
    Write-Output "INVENTORY=$inventory"
    Write-Output "FILES=$($files.Count)"
    Write-Output "BYTES=$($summary.total_bytes)"
    Write-Output ($versions -join '; ')
} finally {
    Remove-Item Env:\C4_REPO_ROOT -ErrorAction SilentlyContinue
    Pop-Location
}
