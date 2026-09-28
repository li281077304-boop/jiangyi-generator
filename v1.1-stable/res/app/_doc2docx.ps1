
param([string]$Src, [string]$Dst)
$ErrorActionPreference = "Stop"
$word = $null; $doc = $null; $wordPid = $null
try {
    $beforePids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $word = New-Object -ComObject Word.Application
    $afterPids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $newPids = $afterPids | Where-Object { $_ -notin $beforePids }
    if ($newPids) { $wordPid = $newPids[0] }
    $word.Visible = $false; $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($Src, [ref]$false, [ref]$true)
    $doc.SaveAs([ref]$Dst, [ref]16)   # 16 = wdFormatDocumentDefault (.docx)
    Write-Output ("OK total=" + $doc.Paragraphs.Count)
} finally {
    if ($doc)  { try { $doc.Close([ref]$false) } catch {} }
    if ($word) { try { $word.Quit() } catch {} }
    if ($word) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
    if ($wordPid) { try { Stop-Process -Id $wordPid -Force -ErrorAction Stop } catch {} }
}
