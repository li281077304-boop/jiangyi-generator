# _scan_com.ps1  ——  用 Word COM 扫描文档段落（保证索引与 _fill_com.ps1 一致）
# 输出：每行 "序号<TAB>文本"，写入 UTF-8 文件
param([string]$DocPath, [string]$OutPath)

$ErrorActionPreference = "Stop"
$word = $null; $doc = $null; $wordPid = $null
try {
    $beforePids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $word = New-Object -ComObject Word.Application
    $afterPids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $newPids = $afterPids | Where-Object { $_ -notin $beforePids }
    if ($newPids) { $wordPid = $newPids[0] }
    $word.Visible = $false; $word.DisplayAlerts = 0

    $doc = $word.Documents.Open($DocPath, [ref]$false, [ref]$true)
    $total = $doc.Paragraphs.Count
    $lines = New-Object System.Collections.Generic.List[string]
    for ($i = 1; $i -le $total; $i++) {
        $t = $doc.Paragraphs.Item($i).Range.Text
        $t = $t -replace "[`r`n`t`f`v]", " "
        $t = $t.Trim()
        $lines.Add("$i`t$t")
    }
    [System.IO.File]::WriteAllLines($OutPath, $lines, (New-Object System.Text.UTF8Encoding($false)))
    Write-Output "TOTAL=$total"
}
finally {
    if ($doc)  { try { $doc.Close([ref]$false) } catch {} }
    if ($word) { try { $word.Quit() } catch {} }
    if ($word) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
    if ($wordPid) { try { Stop-Process -Id $wordPid -Force -ErrorAction Stop } catch {} }
}
