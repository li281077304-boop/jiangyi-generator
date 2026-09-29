# _fill_class.ps1  ——  Word COM 班课模板填充执行器（由 handout.py 调用）
# 参数：-ParamsJson 指向一份 JSON，结构见 handout.py
# 职责：把源文档指定段落范围，原样复制进班课模板(.doc)对应锚点；可选自动套格式。
# 班课模板为 .doc 老格式，65段纯文本表头 + 6模块锚点。
param([string]$ParamsJson)

$ErrorActionPreference = "Stop"
$wdReplaceAll = 2   # Word COM wdReplaceAll 常量
$p = Get-Content $ParamsJson -Raw -Encoding UTF8 | ConvertFrom-Json

# 模板锚点顺序（数字越大越靠后）。填充按从后往前，避免锚点位移。
$ORDER = @{
    "一、课堂启动" = 1; "课堂启动" = 1
    "二、知识回顾" = 2; "知识回顾" = 2
    "知识精讲"     = 3; "知识精讲&例题讲解" = 3
    "即时训练"     = 4
    "五、归纳总结" = 5; "归纳总结" = 5
    "六、巩固练习" = 6; "巩固练习" = 6; "六、出门测试" = 6; "出门测试" = 6
}

$word = $null; $srcDoc = $null; $tplDoc = $null; $wordPid = $null
try {
    $beforePids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $word = New-Object -ComObject Word.Application
    $afterPids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $newPids = $afterPids | Where-Object { $_ -notin $beforePids }
    if ($newPids) { $wordPid = $newPids[0] }
    $word.Visible = $false; $word.DisplayAlerts = 0; $word.ScreenUpdating = $false

    $srcDoc = $word.Documents.Open($p.source_doc, [ref]$false, [ref]$true)
    Write-Output "[$($p.label)] 源文档公式数: $($srcDoc.InlineShapes.Count)"

    $tplDoc = $word.Documents.Open($p.template, [ref]$false, [ref]$false)

    # ——— 班课表头：纯文本段落，用 Find/Replace 替换占位文字 ———
    $replacements = @{}
    if ($p.grade)      { $replacements["五年级"] = $p.grade }
    if ($p.subject)    { $replacements["数学"] = $p.subject }
    if ($p.topic_name) { $replacements["第二单元 因数与倍数"] = $p.topic_name }
    if ($p.objectives) { $replacements["掌握重难点题型"] = $p.objectives }
    if ($p.difficulties) { $replacements["质数和合数的概念以及综合运用"] = $p.difficulties }
    if ($p.authors)    { $replacements["审核老师"] = $p.authors }
    # 年级段标签：原文"五年级"被年级替换后，可能残留班课专用的学段标签
    # 如果目标年级不是"五年级"则需要处理，否则已经在上面的年级替换中处理
    foreach ($findText in $replacements.Keys) {
        $repl = $replacements[$findText]
        if ($repl) {
            $findObj = $tplDoc.Content.Find
            $findObj.ClearFormatting()
            $findObj.Text = $findText
            $null = $findObj.Execute([ref]$findText, [ref]$true, [ref]$true, [ref]$false,
                                      [ref]$false, [ref]$false, [ref]$false, [ref]$false,
                                      [ref]$false, [ref]$repl, [ref]$wdReplaceAll)
        }
    }

    $doFmt = $false
    if ($p.PSObject.Properties.Name -contains "fmt") { $doFmt = [bool]$p.fmt }

    # ——— 按区块填充（从版面后部往前，防锚点位移） ———
    $blocks = $p.blocks | Sort-Object { $ORDER[$_.marker] } -Descending
    foreach ($b in $blocks) {
        if ($b.start -le 0 -or $b.end -lt $b.start) { continue }

        # --- 表格保护：如果 start/end 落在表格内，扩展到整张表 ---
        $adjStart = $b.start; $adjEnd = $b.end
        $sp = $srcDoc.Paragraphs.Item($adjStart)
        if ($sp.Range.Information(12)) {
            $tbl = $sp.Range.Tables.Item(1)
            for ($ti = $adjStart; $ti -ge 1; $ti--) {
                $tp = $srcDoc.Paragraphs.Item($ti)
                if (-not $tp.Range.Information(12)) { break }
                if ($tp.Range.Tables.Item(1).Range.Start -ne $tbl.Range.Start) { break }
                $adjStart = $ti
            }
        }
        $ep = $srcDoc.Paragraphs.Item($adjEnd)
        if ($ep.Range.Information(12)) {
            $tbl2 = $ep.Range.Tables.Item(1)
            $total = $srcDoc.Paragraphs.Count
            for ($ti = $adjEnd; $ti -le $total; $ti++) {
                $tp = $srcDoc.Paragraphs.Item($ti)
                if (-not $tp.Range.Information(12)) { break }
                if ($tp.Range.Tables.Item(1).Range.Start -ne $tbl2.Range.Start) { break }
                $adjEnd = $ti
            }
        }

        $sPos = $srcDoc.Paragraphs.Item($adjStart).Range.Start
        $ePos = $srcDoc.Paragraphs.Item($adjEnd).Range.End
        $rng = $srcDoc.Range($sPos, $ePos)
        $shapeCnt = $rng.InlineShapes.Count
        $rng.Copy()
        $find = $tplDoc.Content.Find
        $find.ClearFormatting(); $find.Text = $b.marker
        if ($find.Execute()) {
            $anchorPara = $find.Parent.Paragraphs.Item(1).Range
            $ins = $tplDoc.Range($anchorPara.End, $anchorPara.End)
            $startPos = $ins.Start
            $ins.Paste()
            $endPos = $ins.End
            Write-Output "  [$($b.marker)] 段$($b.start)-$($b.end) → 已粘贴（公式 $shapeCnt）"

            # ——— 自动套格式 ———
            if ($doFmt -and $endPos -gt $startPos) {
                try {
                    $pasted = $tplDoc.Range($startPos, $endPos)
                    $pasted.ParagraphFormat.LineSpacingRule = 1     # 1.5倍行距
                    $pasted.Font.NameFarEast = "宋体"
                    $pasted.Font.NameAscii   = "Times New Roman"
                    $pasted.Font.NameOther   = "Times New Roman"
                    $pasted.Font.Size        = 10.5                 # 五号字
                    Write-Output "    └ 已套格式"
                } catch {
                    Write-Output "    └ [警告] 套格式失败: $($_.Exception.Message)"
                }
            }
        } else {
            Write-Output "  [警告] 未找到锚点: $($b.marker)"
        }
    }

    # ——— 压缩连续空段（≥2空段压成1个），不伤内容 ———
    $doTrim = $true
    if ($p.PSObject.Properties.Name -contains "trim_blanks") { $doTrim = [bool]$p.trim_blanks }
    if ($doTrim) {
        try {
            $totalParas = $tplDoc.Paragraphs.Count
            $prevEmpty = $false
            for ($pi = $totalParas; $pi -ge 1; $pi--) {
                $pr = $tplDoc.Paragraphs.Item($pi).Range
                $t = $pr.Text.Trim()
                $isEmpty = ($t.Length -eq 0)
                if ($isEmpty -and $prevEmpty -and $pi -lt $totalParas) {
                    try { $pr.Delete() } catch {}
                }
                $prevEmpty = $isEmpty
            }
            Write-Output "  └ 连续空段已压缩"
        } catch {
            Write-Output "  └ [信息] 空段压缩跳过: $($_.Exception.Message)"
        }
    }

    # 班课模板是 .doc → 另存为 .docx
    $tplDoc.SaveAs([ref]$p.output_doc, [ref]16)
    $sq = 0
    foreach ($sh in $tplDoc.InlineShapes) { if ($sh.Width -lt 1 -or $sh.Height -lt 1) { $sq++ } }
    Write-Output "[$($p.label)] 完成: 页=$($tplDoc.ComputeStatistics(2)) 公式=$($tplDoc.InlineShapes.Count) 压扁=$sq"
}
finally {
    if ($tplDoc) { try { $tplDoc.Close([ref]$false) } catch {} }
    if ($srcDoc) { try { $srcDoc.Close([ref]$false) } catch {} }
    if ($word)   { try { $word.Quit() } catch {} }
    if ($word)   { [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
    if ($wordPid) { try { Stop-Process -Id $wordPid -Force -ErrorAction Stop } catch {} }
}
