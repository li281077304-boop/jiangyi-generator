[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$SourcePackageRoot,
    [Parameter(Mandatory=$true)][string]$OutputRoot,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-fA-F]{7,40}$')][string]$BuildCommit,
    [string]$PackageName = '讲义生成器_V1.2_RC.zip',
    [string]$ReadmePath = (Join-Path $PSScriptRoot '..\..\packaging\windows\README_RC.md')
)

$ErrorActionPreference = 'Stop'

function Get-FileInventory([string]$Root) {
    $rootPath = (Resolve-Path -LiteralPath $Root).Path.TrimEnd('\')
    @(Get-ChildItem -LiteralPath $rootPath -File -Recurse | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($rootPath.Length + 1).Replace('\','/')
        [ordered]@{
            path = $relative
            size_bytes = [long]$_.Length
            sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
        }
    })
}

$source = (Resolve-Path -LiteralPath $SourcePackageRoot).Path.TrimEnd('\')
$sourceExe = Join-Path $source '讲义生成器.exe'
if (-not (Test-Path -LiteralPath $sourceExe -PathType Leaf)) {
    throw "Standalone executable is missing: $sourceExe"
}
if (-not (Test-Path -LiteralPath (Join-Path $source '_internal') -PathType Container)) {
    throw 'PyInstaller onedir _internal directory is missing.'
}
if ([IO.Path]::GetFileName($PackageName) -ne $PackageName -or
    [IO.Path]::GetExtension($PackageName) -ne '.zip') {
    throw 'PackageName must be a simple .zip filename.'
}

$output = [IO.Path]::GetFullPath($OutputRoot).TrimEnd('\')
$sourcePrefix = $source.TrimEnd('\') + '\'
if ($output.StartsWith($sourcePrefix, [StringComparison]::OrdinalIgnoreCase) -or
    $source.StartsWith($output.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'OutputRoot and the tested source package must be separate directory trees.'
}
if (Test-Path -LiteralPath $output) {
    throw "OutputRoot must be a new, unused directory: $output"
}
$null = New-Item -ItemType Directory -Path $output

$sourceFiles = Get-FileInventory $source
$sourceTotalBytes = [long]0
foreach ($file in $sourceFiles) { $sourceTotalBytes += [long]$file.size_bytes }
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$v09ManifestPath = Join-Path $repoRoot 'v1.2-xml-experiment\res\app\v09_fallback_runtime\ASSET_MANIFEST.json'
if (-not (Test-Path -LiteralPath $v09ManifestPath -PathType Leaf)) {
    throw "Frozen V0.9 asset manifest is missing: $v09ManifestPath"
}
$v09Manifest = Get-Content -LiteralPath $v09ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$expectedV09TemplateNames = @('2025+1v1讲义模板(2).docx', '2025班课模板.doc')
$v09TemplateAssets = @($v09Manifest.assets | Where-Object { $_.target -in $expectedV09TemplateNames })
$foundV09TemplateNames = @($v09TemplateAssets | ForEach-Object { $_.target } | Sort-Object)
$sortedExpectedV09TemplateNames = @($expectedV09TemplateNames | Sort-Object)
if ($v09TemplateAssets.Count -ne 2 -or
    (($foundV09TemplateNames -join '|') -cne ($sortedExpectedV09TemplateNames -join '|'))) {
    throw 'Frozen V0.9 manifest does not contain exactly the two expected template assets.'
}
$allowedTemplatePaths = @(
    '_internal/v1.1-stable/res/app/2025+1v1讲义模板(2).docx',
    '_internal/v1.1-stable/res/app/2025班课模板.docx',
    '_internal/v1.2-xml-experiment/res/app/v09_fallback_runtime/2025+1v1讲义模板(2).docx',
    '_internal/v1.2-xml-experiment/res/app/v09_fallback_runtime/2025班课模板.doc'
)
$allowedRuntimeDocuments = @(
    '_internal/base_library.zip',
    '_internal/docx/templates/default.docx',
    '_internal/v1.2-xml-experiment/res/app/webapp/static/previews/1v1.pdf',
    '_internal/v1.2-xml-experiment/res/app/webapp/static/previews/class.pdf'
)
$forbidden = @($sourceFiles | Where-Object {
    $_.path -match '(?i)(ocr_models|image_role_evidence|rapidocr|onnxruntime|opencv|/cv2/|/numpy[/.\-]|/shapely[/.\-]|/pyclipper/|\.onnx$)' -or
    $_.path -match '(^|/)(tests?|corpus|gold|\.git|__pycache__|\.pytest_cache|\.venv)(/|$)' -or
    $_.path -match '(^|/)(private|uat|user-data)(/|$)' -or
    ($_.path -match '\.(docx?|pdf|zip)$' -and
        $_.path -notin ($allowedTemplatePaths + $allowedRuntimeDocuments))
})
if ($forbidden.Count -gt 0) {
    throw ('Source package contains forbidden or user-data files: ' + (($forbidden | ForEach-Object path) -join ', '))
}
foreach ($asset in $v09TemplateAssets) {
    $relativePath = '_internal/v1.2-xml-experiment/res/app/v09_fallback_runtime/' + $asset.target
    $templatePath = Join-Path $source ($relativePath.Replace('/', '\'))
    if (-not (Test-Path -LiteralPath $templatePath -PathType Leaf)) {
        throw "Frozen V0.9 template is missing from source package: $relativePath"
    }
    $actualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $templatePath).Hash.ToLowerInvariant()
    if ($actualHash -ne $asset.sha256) {
        throw "Frozen V0.9 template hash mismatch in source package: $relativePath"
    }
}

$readmeSource = $ReadmePath
if (-not (Test-Path -LiteralPath $readmeSource -PathType Leaf)) {
    throw "Release README is missing: $readmeSource"
}

$stageToken = [guid]::NewGuid().ToString('N')
$stage = Join-Path ([IO.Path]::GetTempPath()) ("c4-rc-stage-" + $stageToken)
$stagePackage = Join-Path $stage '讲义生成器'
$zipPath = Join-Path $output $PackageName
$reportPath = Join-Path $output 'RC_PACKAGE_REPORT.json'
try {
    $null = New-Item -ItemType Directory -Path $stagePackage -Force
    Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $stagePackage -Recurse -Force
    Copy-Item -LiteralPath $readmeSource -Destination (Join-Path $stage 'README.md')

    $stagedFiles = Get-FileInventory $stagePackage
    if ($sourceFiles.Count -ne $stagedFiles.Count) {
        throw 'Staged package file count differs from the tested source onedir.'
    }
    for ($index = 0; $index -lt $sourceFiles.Count; $index++) {
        if ($sourceFiles[$index].path -ne $stagedFiles[$index].path -or
            $sourceFiles[$index].size_bytes -ne $stagedFiles[$index].size_bytes -or
            $sourceFiles[$index].sha256 -ne $stagedFiles[$index].sha256) {
            throw "Staged onedir differs from the tested source at index $index."
        }
    }

    $runtimeFiles = @((Get-FileInventory $stage))
    $manifest = [ordered]@{
        package_name = $PackageName
        build_commit = $BuildCommit.ToLowerInvariant()
        readme = 'README.md'
        onedir_file_count = $stagedFiles.Count
        onedir_total_bytes = $sourceTotalBytes
        files = $runtimeFiles
    }
    $manifest | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $stage 'PACKAGE_MANIFEST.json') -Encoding UTF8

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::CreateFromDirectory(
        $stage, $zipPath, [IO.Compression.CompressionLevel]::Optimal, $false)
    if (-not (Test-Path -LiteralPath $zipPath -PathType Leaf) -or (Get-Item -LiteralPath $zipPath).Length -le 0) {
        throw 'RC ZIP was not created or is empty.'
    }

    $archive = [IO.Compression.ZipFile]::OpenRead($zipPath)
    try {
        $entryNames = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\\','/') })
        foreach ($requiredEntry in @('README.md', 'PACKAGE_MANIFEST.json', '讲义生成器/讲义生成器.exe')) {
            if ($requiredEntry -notin $entryNames) { throw "RC ZIP is missing required entry: $requiredEntry" }
        }
        $zipForbidden = @($entryNames | Where-Object {
            $_ -match '(?i)(ocr_models|image_role_evidence|rapidocr|onnxruntime|opencv|/cv2/|/numpy[/.\-]|/shapely[/.\-]|/pyclipper/|\.onnx$)' -or
            $_ -match '(^|/)(tests?|corpus|gold|\.git|__pycache__|\.pytest_cache|\.venv)(/|$)' -or
            $_ -match '(^|/)(private|uat|user-data)(/|$)' -or
            ($_ -match '\.(docx?|pdf|zip)$' -and $_ -notin (@(
                '讲义生成器/_internal/v1.1-stable/res/app/2025+1v1讲义模板(2).docx',
                '讲义生成器/_internal/v1.1-stable/res/app/2025班课模板.docx',
                '讲义生成器/_internal/v1.2-xml-experiment/res/app/v09_fallback_runtime/2025+1v1讲义模板(2).docx',
                '讲义生成器/_internal/v1.2-xml-experiment/res/app/v09_fallback_runtime/2025班课模板.doc'
            ) + @($allowedRuntimeDocuments | ForEach-Object { '讲义生成器/' + $_ })))
        })
        if ($zipForbidden.Count -gt 0) {
            throw ('RC ZIP contains forbidden content: ' + ($zipForbidden -join ', '))
        }
        foreach ($asset in $v09TemplateAssets) {
            $entryName = '讲义生成器/_internal/v1.2-xml-experiment/res/app/v09_fallback_runtime/' + $asset.target
            $entry = $archive.GetEntry($entryName)
            if ($null -eq $entry) { throw "RC ZIP is missing frozen V0.9 template: $entryName" }
            $entryStream = $entry.Open()
            $sha = [Security.Cryptography.SHA256]::Create()
            try {
                $actualHash = -join ($sha.ComputeHash($entryStream) | ForEach-Object { $_.ToString('x2') })
            }
            finally {
                $entryStream.Dispose()
                $sha.Dispose()
            }
            if ($actualHash -ne $asset.sha256) {
                throw "Frozen V0.9 template hash mismatch inside RC ZIP: $entryName"
            }
        }
    }
    finally {
        $archive.Dispose()
    }

    $zipHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLowerInvariant()
    $exeHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $stagePackage '讲义生成器.exe')).Hash.ToLowerInvariant()
    $report = [ordered]@{
        status = 'PACKAGED'
        package_name = $PackageName
        package_path = $zipPath
        package_size_bytes = [long](Get-Item -LiteralPath $zipPath).Length
        package_sha256 = $zipHash
        exe_sha256 = $exeHash
        build_commit = $BuildCommit.ToLowerInvariant()
        tested_onedir_source = $source
        onedir_file_count = $stagedFiles.Count
        onedir_total_bytes = $manifest.onedir_total_bytes
        package_manifest_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $stage 'PACKAGE_MANIFEST.json')).Hash.ToLowerInvariant()
        readme_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $stage 'README.md')).Hash.ToLowerInvariant()
        excluded_content_scan = 'PASS'
        source_to_stage_hash_comparison = 'PASS'
        frozen_v09_templates_verified = 2
    }
    $report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    Write-Output "RC_ZIP=$zipPath"
    Write-Output "RC_SHA256=$zipHash"
    Write-Output "RC_SIZE=$($report.package_size_bytes)"
    Write-Output "REPORT=$reportPath"
}
finally {
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    $stageFull = [IO.Path]::GetFullPath($stage)
    if ($stageFull.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and
        (Split-Path -Leaf $stageFull) -eq ("c4-rc-stage-" + $stageToken) -and
        (Test-Path -LiteralPath $stageFull)) {
        Remove-Item -LiteralPath $stageFull -Recurse -Force
    }
}
