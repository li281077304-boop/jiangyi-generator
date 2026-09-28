# _strip_answer_com.ps1  ——  用 Word COM 删除答案段落（生成学生版）
# 由 handout.make_student() 调用。
# 规则：找到【答案】/【详解】等标记 → 删除该段及其后所有内容直到遇到真正的章节分界
# 章节分界：中文序号标题（一、二、…）/ 题型标记 / 文档末尾
# 答案区内的子编号（(1)(2)①A.等）不算分界，避免只删标记行而漏掉答案正文
param([string]$SrcPath, [string]$OutPath)

$ErrorActionPreference = "Stop"

# 答案标记：段落开头或段中含有这些关键词
$ANS_RE = '【答案】|【详解】|【解析】|参考答案[：:．]|参考解析[：:．]|【解答】|[（(]\s*(?:答案|详解|解析)\s*[）)]|【解答】'
# 真正的章节分界（遇到就停止删除）：中文序号标题 / 知识/题型/考点标记
$SECTION_RE = '^\s*[一二三四五六七八九十]+[、.．]\s*\S'
# 题型/考点等板块标记（也是真正的分界）
$TOPIC_RE = '^\s*(题型|考点|知识点|专题|Part|Section|Lesson|Unit)\s*\d*'

$word = $null; $doc = $null; $wordPid = $null
try {
    # 记录启动前已有 WINWORD 进程
    $beforePids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $word = New-Object -ComObject Word.Application
    $afterPids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $newPids = $afterPids | Where-Object { $_ -notin $beforePids }
    if ($newPids) { $wordPid = $newPids[0] }
    $word.Visible = $false; $word.DisplayAlerts = 0; $word.ScreenUpdating = $false

    $doc = $word.Documents.Open($SrcPath, [ref]$false, [ref]$true)
    $total = $doc.Paragraphs.Count

    # Step 1: 收集答案标记段和章节分界的位置
    $answerSpots = New-Object System.Collections.Generic.List[int]
    $sectionSpots = New-Object System.Collections.Generic.List[int]

    for ($i = 1; $i -le $total; $i++) {
        $t = ($doc.Paragraphs.Item($i).Range.Text) -replace "[\r\n\t\f\v]", " "
        $t = $t.Trim()
        if ($t -match $ANS_RE) {
            $answerSpots.Add($i)
        }
        if ($t -match $SECTION_RE -or $t -match $TOPIC_RE) {
            $sectionSpots.Add($i)
        }
    }

    if ($answerSpots.Count -eq 0) {
        Write-Output "NO_ANSWER_MARK"
    } else {
        # Step 2: 构建删除区间：[答案段 → 下一个章节分界或文档末尾]
        $deleteRanges = New-Object System.Collections.Generic.List[object]
        foreach ($aIdx in $answerSpots) {
            # 找第一个大于此答案的章节分界
            $nextSec = $total + 1
            foreach ($s in $sectionSpots) {
                if ($s -gt $aIdx -and $s -lt $nextSec) { $nextSec = $s }
            }
            $endIdx = $nextSec - 1
            if ($endIdx -lt $aIdx) { $endIdx = $aIdx }
            # 合并重叠区间
            $merged = $false
            foreach ($dr in $deleteRanges) {
                if ($aIdx -le $dr.EndIdx -and $endIdx -ge $dr.StartIdx) {
                    $dr.StartIdx = [Math]::Min($dr.StartIdx, $aIdx)
                    $dr.EndIdx   = [Math]::Max($dr.EndIdx, $endIdx)
                    $merged = $true; break
                }
            }
            if (-not $merged) {
                $deleteRanges.Add((New-Object PSObject -Property @{StartIdx=$aIdx; EndIdx=$endIdx}))
            }
        }

        # Step 3: 从后往前删
        $deleted = 0
        $deleteRanges = $deleteRanges | Sort-Object StartIdx -Descending
        foreach ($dr in $deleteRanges) {
            for ($i = $dr.EndIdx; $i -ge $dr.StartIdx; $i--) {
                try {
                    $doc.Paragraphs.Item($i).Range.Delete() | Out-Null
                    $deleted++
                } catch {}
            }
        }

        # Step 4: 压缩连续空段
        $total2 = $doc.Paragraphs.Count
        $prevEmpty = $false
        for ($i = $total2; $i -ge 2; $i--) {
            try {
                $ti = $doc.Paragraphs.Item($i).Range.Text.Trim()
                $isEmpty = ($ti.Length -eq 0)
                if ($isEmpty -and $prevEmpty) {
                    try { $doc.Paragraphs.Item($i).Range.Delete() | Out-Null } catch {}
                }
                $prevEmpty = $isEmpty
            } catch { continue }
        }

        Write-Output "MARKS=$($answerSpots.Count) RANGES=$($deleteRanges.Count) DELETED=$deleted"
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
    if ($wordPid) { try { Stop-Process -Id $wordPid -Force -ErrorAction Stop } catch {} }
}
