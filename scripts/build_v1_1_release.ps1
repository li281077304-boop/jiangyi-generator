[CmdletBinding()]
param(
    [string]$OutputDirectory = '',
    [string]$Python312 = '',
    [string]$BuildRoot = ''
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $repoRoot 'dist'
}
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)

function Invoke-Checked {
    param([string]$FilePath, [string[]]$Arguments)
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "命令失败（$LASTEXITCODE）：$FilePath $($Arguments -join ' ')"
    }
}

function Find-Python312 {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        if (-not (Test-Path -LiteralPath $RequestedPath -PathType Leaf)) {
            throw "找不到构建用 Python：$RequestedPath"
        }
        return [IO.Path]::GetFullPath($RequestedPath)
    }

    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        $resolved = & $launcher.Source -3.12 -c 'import sys; print(sys.executable)'
        if ($LASTEXITCODE -eq 0 -and $resolved -and (Test-Path -LiteralPath $resolved)) {
            return [IO.Path]::GetFullPath($resolved.Trim())
        }
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $candidate = $pythonCommand.Source
        $info = & $candidate -c 'import struct,sys; print(sys.version_info[0],sys.version_info[1],struct.calcsize(chr(80))*8)'
        if ($LASTEXITCODE -eq 0 -and (($info -join ' ').Trim() -eq '3 12 64')) {
            return $candidate
        }
    }
    throw '构建机需要 Python 3.12 x64 和 pip。可用 -Python312 指定 python.exe；最终发布包不依赖构建机 Python。'
}

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot '.git'))) {
    throw "不是 Git 工作区：$repoRoot"
}
$status = & git -C $repoRoot status --porcelain
if ($LASTEXITCODE -ne 0) { throw '无法读取 Git 工作区状态。' }
if ($status) { throw '发布构建要求干净的 Git 工作区；请先提交或清理变更。' }

$sourceCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $sourceCommit -notmatch '^[0-9a-f]{40}$') {
    throw '无法确定发布源 HEAD。'
}

$pythonBuilder = Find-Python312 $Python312
$builderInfo = (& $pythonBuilder -c 'import struct,sys; print(sys.version_info[0],sys.version_info[1],struct.calcsize(chr(80))*8)' | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $builderInfo -ne '3 12 64') {
    throw "构建 Python 必须是 3.12 x64，当前为：$builderInfo"
}
& $pythonBuilder -m pip --version | Out-Null
if ($LASTEXITCODE -ne 0) { throw '构建 Python 缺少 pip。' }

$releaseVersion = '3.12.10'
$runtimeFile = "python-$releaseVersion-embed-amd64.zip"
$runtimeUrl = "https://www.python.org/ftp/python/$releaseVersion/$runtimeFile"
$runtimeSha256 = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3' # official .sigstore SHA2_256
$requirementsFile = Join-Path $repoRoot 'packaging\requirements-v1.1.lock'
if (-not (Test-Path -LiteralPath $requirementsFile -PathType Leaf)) {
    throw "找不到依赖锁文件：$requirementsFile"
}

# Build scratch root. Resolution order:
#   -BuildRoot  ->  $env:JY_BUILD_ROOT  ->  H:\AI-Workspace\tmp\build (if present)
#   ->  system temp directory.
# Rationale: packaging used to write its whole intermediate tree under
# [IO.Path]::GetTempPath(), which filled the C: drive.
if (-not $BuildRoot) {
    if ($env:JY_BUILD_ROOT) {
        $BuildRoot = $env:JY_BUILD_ROOT
    } elseif (Test-Path 'H:\AI-Workspace\tmp\build') {
        $BuildRoot = 'H:\AI-Workspace\tmp\build'
    } else {
        $BuildRoot = [IO.Path]::GetTempPath()
    }
}
$BuildRoot = [IO.Path]::GetFullPath($BuildRoot)
New-Item -ItemType Directory -Path $BuildRoot -Force | Out-Null
$buildRoot = Join-Path $BuildRoot ("jiangyi-v1.1-build-" + [Guid]::NewGuid().ToString('N'))
$packageRoot = Join-Path $buildRoot 'package'
$releaseRoot = Join-Path $packageRoot 'v1.1-stable'
$runtimeRoot = Join-Path $releaseRoot 'res\python'
$sitePackages = Join-Path $runtimeRoot 'Lib\site-packages'
New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null

try {
    $trackedFiles = @(& git -c core.quotepath=false -C $repoRoot ls-files -- 'v1.1-stable')
    if ($LASTEXITCODE -ne 0 -or $trackedFiles.Count -eq 0) {
        throw '无法枚举 Git 跟踪的 v1.1-stable 发布文件。'
    }
    foreach ($relativePath in $trackedFiles) {
        $sourcePath = [IO.Path]::GetFullPath([IO.Path]::Combine($repoRoot, $relativePath.Replace('/', '\')))
        if (-not $sourcePath.StartsWith($repoRoot, [StringComparison]::OrdinalIgnoreCase)) {
            throw "拒绝复制工作区外的路径：$relativePath"
        }
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            throw "Git 跟踪文件缺失：$relativePath"
        }
        $targetPath = [IO.Path]::Combine($packageRoot, $relativePath.Replace('/', '\'))
        New-Item -ItemType Directory -Path (Split-Path -Parent $targetPath) -Force | Out-Null
        Copy-Item -LiteralPath $sourcePath -Destination $targetPath
    }

    $runtimeZip = Join-Path $buildRoot $runtimeFile
    Write-Host "下载官方 CPython $releaseVersion embeddable package..."
    Invoke-WebRequest -Uri $runtimeUrl -OutFile $runtimeZip -UseBasicParsing
    $actualSha256 = (Get-FileHash -LiteralPath $runtimeZip -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $runtimeSha256) {
        throw "CPython runtime SHA256 不匹配：$actualSha256"
    }
    Expand-Archive -LiteralPath $runtimeZip -DestinationPath $runtimeRoot -Force

    $pythonExe = Join-Path $runtimeRoot 'python.exe'
    $pthFile = Join-Path $runtimeRoot 'python312._pth'
    if (-not (Test-Path -LiteralPath $pythonExe) -or -not (Test-Path -LiteralPath $pthFile)) {
        throw '官方 runtime 缺少 python.exe 或 python312._pth。'
    }
    $pthContents = "python312.zip`r`n.`r`nLib\site-packages`r`nimport site`r`n"
    [IO.File]::WriteAllText($pthFile, $pthContents, [Text.Encoding]::ASCII)

    New-Item -ItemType Directory -Path $sitePackages -Force | Out-Null
    Write-Host '安装锁定的 Flask、Waitress、python-docx 和项目运行依赖...'
    Invoke-Checked $pythonBuilder @(
        '-m', 'pip', 'install', '--disable-pip-version-check', '--no-compile',
        '--only-binary=:all:', '--target', $sitePackages, '-r', $requirementsFile
    )

    Write-Host '校验隔离 Python runtime 和依赖导入...'
    Invoke-Checked $pythonExe @('-c', 'import flask,waitress,docx,lxml,requests')

    $webApp = Join-Path $releaseRoot 'res\app\webapp'
    $engine = Join-Path $releaseRoot 'res\app'
    Invoke-Checked $pythonExe @((Join-Path $webApp 'test_app_api.py'))
    Invoke-Checked $pythonExe @((Join-Path $webApp 'test_template_config.py'))
    Invoke-Checked $pythonExe @((Join-Path $engine 'test_student_ops.py'))
    Invoke-Checked $pythonExe @('-m', 'compileall', '-q', $engine)

    $manifest = [ordered]@{
        sourceCommit = $sourceCommit
        pythonVersion = $releaseVersion
        pythonDistribution = $runtimeFile
        architecture = 'win_amd64'
        builtUtc = [DateTime]::UtcNow.ToString('o')
        requirementsLock = 'packaging/requirements-v1.1.lock'
    }
    $manifestJson = $manifest | ConvertTo-Json -Depth 4
    [IO.File]::WriteAllText((Join-Path $releaseRoot 'release-manifest.json'), $manifestJson, [Text.UTF8Encoding]::new($true))

    Get-ChildItem -LiteralPath $releaseRoot -Directory -Filter '__pycache__' -Recurse | Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $releaseRoot -Directory -Filter 'logs' -Recurse | Remove-Item -Recurse -Force

    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $zipPath = Join-Path $OutputDirectory ("jiangyi-generator-v1.1-$($sourceCommit.Substring(0,12))-win-x64.zip")
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -Path $releaseRoot -DestinationPath $zipPath -CompressionLevel Optimal

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        $requiredEntries = @(
            'v1.1-stable/启动讲义生成器.vbs',
            'v1.1-stable/res/python/python.exe',
            'v1.1-stable/res/python/python312.zip',
            'v1.1-stable/res/python/python312.dll',
            'v1.1-stable/res/python/Lib/site-packages/flask/__init__.py',
            'v1.1-stable/res/python/Lib/site-packages/waitress/__init__.py',
            'v1.1-stable/res/python/Lib/site-packages/docx/__init__.py'
        )
        $entryNames = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\', '/') })
        foreach ($requiredEntry in $requiredEntries) {
            if ($entryNames -notcontains $requiredEntry) { throw "发布 ZIP 缺少文件：$requiredEntry" }
        }
    } finally {
        $archive.Dispose()
    }
    $zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.File]::WriteAllText(($zipPath + '.sha256'), "$zipHash  $([IO.Path]::GetFileName($zipPath))`r`n", [Text.Encoding]::ASCII)
    Write-Host "发布包：$zipPath"
    Write-Host "SHA256：$zipHash"
} finally {
    if (Test-Path -LiteralPath $buildRoot) {
        Remove-Item -LiteralPath $buildRoot -Recurse -Force
    }
}
