# _renumber_com.ps1  ——  用 Word COM 重编号（顺序与填充完全一致）
# 规则：扫描全部段落，匹配真题号（数字+点号+括号年份），按出现顺序从 1 重编，
#       只替换题号数字部分（Range.Text），保留其余文本与段落格式。
param([string]$SrcPath, [string]$OutPath)

$ErrorActionPreference = "Stop"
$word = $null; $doc = $null; $wordPid = $null
try {
    $beforePids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $word = New-Object -ComObject Word.Application
    $afterPids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $newPids = $afterPids | Where-Object { $_ -notin $beforePids }
    if ($newPids) { $wordPid = $newPids[0] }
    $word.Visible = $false; $word.DisplayAlerts = 0

    $doc = $word.Documents.Open($SrcPath, [ref]$false, [ref]$true)
    $total = $doc.Paragraphs.Count
    $qnumRe = '^\s*\d{1,3}\s*[.．、]\s*[（(]\s*(20\d\d|\d{2}-)'
    $digitRe = '^\s*\d{1,3}'
    $n = 0
    for ($i = 1; $i -le $total; $i++) {
        $para = $doc.Paragraphs.Item($i)
        $t = $para.Range.Text -replace '[\u0000-\u001F]', ' '
        if ($t -notmatch $qnumRe) { continue }
        $n++
        $m = [regex]::Match($t, $digitRe)
        if ($m.Success) {
            $abs = $para.Range.Start + $m.Index
            $rng = $doc.Range($abs, $abs + $m.Length)
            $rng.Text = [string]$n
        }
    }
    $doc.SaveAs([ref]$OutPath, [ref]16)
    Write-Output "RENUMBERED=$n"
}
finally {
    if ($doc)  { try { $doc.Close([ref]$false) } catch {} }
    if ($word) { try { $word.Quit() } catch {} }
    if ($word) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
    if ($wordPid) { try { Stop-Process -Id $wordPid -Force -ErrorAction Stop } catch {} }
}
