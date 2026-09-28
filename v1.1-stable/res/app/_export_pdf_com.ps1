# Export a Word document to PDF using Word COM.
param(
    [Parameter(Mandatory=$true)][string]$DocPath,
    [Parameter(Mandatory=$true)][string]$PdfPath
)

$ErrorActionPreference = "Stop"
$word = $null
$doc = $null
$wordPid = $null

try {
    $beforePids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $word = New-Object -ComObject Word.Application
    $afterPids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $newPids = $afterPids | Where-Object { $_ -notin $beforePids }
    if ($newPids) { $wordPid = $newPids[0] }

    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.ScreenUpdating = $false

    $doc = $word.Documents.Open((Resolve-Path $DocPath).Path, [ref]$false, [ref]$true)
    $pageCount = $doc.ComputeStatistics(2)
    $inlineShapes = $doc.InlineShapes.Count
    $tables = $doc.Tables.Count
    $paras = $doc.Paragraphs.Count

    $outDir = Split-Path -Parent $PdfPath
    if ($outDir -and -not (Test-Path $outDir)) {
        New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    }

    # wdExportFormatPDF = 17
    $doc.ExportAsFixedFormat((Resolve-Path $outDir).Path + "\" + (Split-Path -Leaf $PdfPath), 17)
    Write-Output "PAGES=$pageCount"
    Write-Output "PARAGRAPHS=$paras"
    Write-Output "TABLES=$tables"
    Write-Output "INLINE_SHAPES=$inlineShapes"
    Write-Output "PDF=$PdfPath"
}
finally {
    if ($doc) { try { $doc.Close([ref]$false) } catch {} }
    if ($word) { try { $word.Quit() } catch {} }
    if ($word) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
    if ($wordPid) {
        try { Stop-Process -Id $wordPid -Force -ErrorAction Stop } catch {}
    }
}
