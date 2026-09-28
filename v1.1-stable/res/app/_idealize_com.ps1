# _idealize_com.ps1  ——  例题提取（题型清单式文档专用）
# 规则：每个「题型」标题后的第一道题（题号段+其答案详解，到下一题号/题型前）视为例题，整组删除；
#       剩余题目保持原顺序（重编号由 Python 端处理，保留 run 格式）。
# 输出：另存到 OutPath；控制台打印每题型删除的段落范围。
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

    # 收集段落文本
    $texts = @()
    for ($i = 1; $i -le $total; $i++) {
        $t = $doc.Paragraphs.Item($i).Range.Text
        $t = $t -replace '_x[0-9A-Fa-f]{4}_', ''
        $t = $t -replace "[\u0000-\u001F]", ' '
        $texts += $t.Trim()
    }

    $typeRe   = '^【题型\s*\d+'
    # 真题号强特征：行首数字 + 句号/顿号 + 左括号 + 年份（2025 / 24-25 等）
    $qnumRe   = '^\s*\d{1,3}\s*[.．、]\s*[（(]\s*(20\d\d|\d{2}-)'

    # 逐题型处理：每个题型只提取「第一道题」为例题（例题起点 .. 第二题号前）
    $groups = @()
    $curType = $false
    $firstQ = -1
    $exTaken = $false
    for ($i = 1; $i -le $total; $i++) {
        $t = $texts[$i-1]
        if ($t -match $typeRe) {
            $curType = $true; $firstQ = -1; $exTaken = $false
            continue
        }
        if ($curType -and -not $exTaken -and $t -match $qnumRe) {
            if ($firstQ -eq -1) { $firstQ = $i }
            else {
                $groups += @{ Start = $firstQ; End = $i - 1 }
                $exTaken = $true
            }
        }
    }
    if ($curType -and -not $exTaken -and $firstQ -ge 1) {
        $groups += @{ Start = $firstQ; End = $total }
    }

    # 汇总每个题型的例题组（每组连续）
    $summary = @()
    foreach ($g in $groups) {
        $summary += "例题组: $($g.Start)..$($g.End)"
    }
    [System.IO.File]::WriteAllLines($OutPath + ".summary.txt", $summary, (New-Object System.Text.UTF8Encoding($false)))

    # 安全保护：例题组覆盖段数超总段数 40% 视为识别错误，中止
    $cover = ($groups | ForEach-Object { $_.End - $_.Start + 1 } | Measure-Object -Sum).Sum
    if ($cover -gt $total * 0.4) {
        throw "例题覆盖比例异常 ($cover/$total)，疑似题号误识别，已中止。"
    }

    # 倒序删除（避免索引变化）
    $sorted = $groups | Sort-Object { $_.Start } -Descending
    $deleted = 0
    foreach ($g in $sorted) {
        for ($k = $g.End; $k -ge $g.Start; $k--) {
            try {
                $doc.Paragraphs.Item($k).Range.Delete() | Out-Null
                $deleted++
            } catch { }
        }
    }

    $doc.SaveAs([ref]$OutPath, [ref]16)   # 16 = wdFormatDocumentDefault (.docx)
    Write-Output "DELETED=$deleted GROUPS=$($groups.Count)"
}
finally {
    if ($doc)  { try { $doc.Close([ref]$false) } catch {} }
    if ($word) { try { $word.Quit() } catch {} }
    if ($word) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
    if ($wordPid) { try { Stop-Process -Id $wordPid -Force -ErrorAction Stop } catch {} }
}
