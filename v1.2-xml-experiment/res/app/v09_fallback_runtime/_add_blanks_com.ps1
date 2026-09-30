# _add_blanks_com.ps1  --  Word COM add blank lines for short-answer questions
param([string]$SrcPath, [string]$OutPath)

$ErrorActionPreference = "Stop"

$QNUM_RE = '^\s*\d{1,3}\s*[.．、]'
$QNUM_PAREN_RE = '^\s*[（(]\s*\d+\s*[）)]'

$word = $null; $doc = $null; $wordPid = $null
try {
    # 记录启动前已有 WINWORD 进程（避免误杀用户正在编辑的文档）
    $beforePids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $word = New-Object -ComObject Word.Application
    $afterPids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $newPids = $afterPids | Where-Object { $_ -notin $beforePids }
    if ($newPids) { $wordPid = $newPids[0] }
    $word.Visible = $false; $word.DisplayAlerts = 0; $word.ScreenUpdating = $false

    $doc = $word.Documents.Open($SrcPath, [ref]$false, [ref]$true)
    $total = $doc.Paragraphs.Count

    # Collect question headers
    $qHeaders = New-Object System.Collections.Generic.List[int]
    for ($i = 1; $i -le $total; $i++) {
        $t = ($doc.Paragraphs.Item($i).Range.Text) -replace "[\r\n\t\f\v]", " "
        $t = $t.Trim()
        if (-not $t) { continue }
        if ($t -match $QNUM_RE -or $t -match $QNUM_PAREN_RE) {
            $null = $qHeaders.Add($i)
        }
    }

    if ($qHeaders.Count -eq 0) {
        Write-Output "NO_QUESTIONS_FOUND"
    } else {
        # Classify each question: choice / blank / shortanswer
        $saQs = New-Object System.Collections.Generic.List[int]
        $subCounts = New-Object System.Collections.Generic.List[int]

        for ($qi = 0; $qi -lt $qHeaders.Count; $qi++) {
            $qStart = $qHeaders[$qi]
            $qEnd = $total
            if ($qi + 1 -lt $qHeaders.Count) {
                $qEnd = $qHeaders[$qi + 1] - 1
            }

            $hasChoice = $false
            $hasBlank = $false
            $subCount = 1
            $sawFirstSub = $false

            for ($j = $qStart; $j -le $qEnd; $j++) {
                $tt = ($doc.Paragraphs.Item($j).Range.Text) -replace "[\r\n\t\f\v]", " "
                $tt = $tt.Trim()
                if ($tt -match '^[A-D][.．、]') { $hasChoice = $true }
                if ($tt -match '___|____|（\s*）|\(\s*\)') { $hasBlank = $true }
                if ($tt -match $QNUM_PAREN_RE) {
                    if ($j -gt $qStart -or -not $sawFirstSub) {
                        if ($sawFirstSub) { $subCount++ }
                        $sawFirstSub = $true
                    }
                }
            }

            if (-not $hasChoice -and -not $hasBlank) {
                $null = $saQs.Add($qStart)
                $null = $subCounts.Add($subCount)
            }
        }

        if ($saQs.Count -eq 0) {
            Write-Output "NO_SHORT_ANSWER"
        } else {
            # Insert blanks from back to front to avoid index drift
            $inserted = 0
            for ($si = $saQs.Count - 1; $si -ge 0; $si--) {
                $qStart = $saQs[$si]
                $sub = $subCounts[$si]
                $blankLines = 3 * $sub

                # Find question end
                $qi = $qHeaders.IndexOf($qStart)
                $qEnd = $total
                if ($qi -ge 0 -and $qi + 1 -lt $qHeaders.Count) {
                    $qEnd = $qHeaders[$qi + 1] - 1
                }

                $refPara = $doc.Paragraphs.Item($qEnd)
                $refRng = $doc.Range($refPara.Range.End, $refPara.Range.End)
                for ($k = 1; $k -le $blankLines; $k++) {
                    $refRng.InsertParagraphAfter() | Out-Null
                    $inserted++
                }
            }

            Write-Output "SHORT_ANSWER=$($saQs.Count) BLANKS=$inserted"
        }
    }

    $sq = 0
    foreach ($sh in $doc.InlineShapes) { if ($sh.Width -lt 1 -or $sh.Height -lt 1) { $sq++ } }
    $doc.SaveAs([ref]$OutPath, [ref]16)
    Write-Output "DONE 公式=$($doc.InlineShapes.Count) 压扁=$sq"
}
finally {
    if ($doc)  { try { $doc.Close([ref]$false) } catch {} }
    if ($word) { try { $word.Quit() } catch {} }
    if ($word) { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
    # 仅清理我们启动的 Word 进程
    if ($wordPid) {
        try { Stop-Process -Id $wordPid -Force -ErrorAction Stop } catch {}
    }
}