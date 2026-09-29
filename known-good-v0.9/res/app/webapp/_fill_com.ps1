# _fill_com.ps1  ——  Word COM 通用填充执行器（由 handout.py 调用）
# 参数：-ParamsJson 指向一份 JSON，结构见 handout.py
# 职责：把源文档指定段落范围，原样复制进模板对应锚点；可选自动套格式。
param([string]$ParamsJson)

$ErrorActionPreference = "Stop"
$p = Get-Content $ParamsJson -Raw -Encoding UTF8 | ConvertFrom-Json

# 模板锚点在版面中的先后顺序（数字越大越靠后）。填充按从后往前，避免锚点位移。
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
    # 记录启动前已有 WINWORD 进程（避免误杀用户正在编辑的文档）
    $beforePids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $word = New-Object -ComObject Word.Application
    # 找到我们刚启动的 Word 进程 PID
    $afterPids = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    $newPids = $afterPids | Where-Object { $_ -notin $beforePids }
    if ($newPids) { $wordPid = $newPids[0] }
    $word.Visible = $false; $word.DisplayAlerts = 0; $word.ScreenUpdating = $false

    $srcDoc = $word.Documents.Open($p.source_doc, [ref]$false, [ref]$true)
    Write-Output "[$($p.label)] 源文档公式数: $($srcDoc.InlineShapes.Count)"

    $tplDoc = $word.Documents.Open($p.template, [ref]$false, [ref]$false)

    # ——— 头部信息填充（支持 1v1 模板表格 + 班课模板文本替换） ———
    $templateType = "1v1"
    if ($p.PSObject.Properties.Name -contains "template_type") { $templateType = $p.template_type }

    if ($templateType -eq "class") {
        # 班课模板：表头是纯文本段落 → 查找占位文字替换
        $replacements = @{}
        if ($p.grade)      { $replacements["五年级"] = $p.grade }
        if ($p.subject)    { $replacements["数学"] = $p.subject }
        if ($p.topic_name) { $replacements["第二单元 因数与倍数"] = $p.topic_name }
        if ($p.objectives) { $replacements["掌握重难点题型"] = $p.objectives }
        if ($p.difficulties) { $replacements["质数和合数的概念以及综合运用"] = $p.difficulties }
        foreach ($find in $replacements.Keys) {
            $repl = $replacements[$find]
            if ($repl) {
                $findObj = $tplDoc.Content.Find
                $findObj.ClearFormatting()
                $findObj.Text = $find
                $null = $findObj.Execute([ref]$find, [ref]$true, [ref]$true, [ref]$false,
                                        [ref]$false, [ref]$false, [ref]$false, [ref]$false,
                                        [ref]$false, [ref]$repl, [ref]$wdReplaceAll)
            }
        }
    } else {
        # 1v1 模板：表格形式
        try {
            $tbl = $tplDoc.Tables.Item(1)
            # 行1：科目(列1)、年级(列2)
            try { if ($p.subject)    { $cell = $tbl.Cell(1,1).Range; $cell.Text = "科 目：$($p.subject)" } } catch {}
            try { if ($p.grade)      { $tbl.Cell(1,2).Range.Text = $p.grade } } catch {}
            # 行2：授课主题(列2)、课程类型(列4)
            try { if ($p.topic_name) { $tbl.Cell(2,2).Range.Text = $p.topic_name } } catch {}
            try { if ($p.handout_type) { $tbl.Cell(2,4).Range.Text = $p.handout_type } } catch {}
            # 行3-4：教学目标、重点难点
            try { if ($p.objectives)   { $tbl.Cell(3,2).Range.Text = $p.objectives } }    catch {}
            try { if ($p.difficulties) { $tbl.Cell(4,2).Range.Text = $p.difficulties } }  catch {}
        } catch {
            Write-Output "  [信息] 模板无表格，跳过表头填充"
        }
    }

    $doFmt = $false
    if ($p.PSObject.Properties.Name -contains "fmt") { $doFmt = [bool]$p.fmt }

    # ——— 按区块填充（从版面后部往前，防锚点位移） ———
    $blocks = $p.blocks | Sort-Object { $ORDER[$_.marker] } -Descending
    foreach ($b in $blocks) {
        if ($b.start -le 0 -or $b.end -lt $b.start) { continue }

        # --- 表格保护：如果 start 或 end 落在表格内，扩展到整张表的边界 ---
        $adjStart = $b.start
        $adjEnd   = $b.end

        $sp = $srcDoc.Paragraphs.Item($adjStart)
        if ($sp.Range.Information(12)) {   # wdWithInTable = 12，段在表格内
            $tbl = $sp.Range.Tables.Item(1)
            # 找这张表的第一段
            for ($ti = $adjStart; $ti -ge 1; $ti--) {
                $tp = $srcDoc.Paragraphs.Item($ti)
                if (-not $tp.Range.Information(12)) { break }
                $ttbl = $tp.Range.Tables.Item(1)
                if ($ttbl.Range.Start -ne $tbl.Range.Start) { break }
                $adjStart = $ti
            }
            Write-Output "  ┌ start 段$($b.start)在表格内，扩展到表首段$adjStart"
        }

        $ep = $srcDoc.Paragraphs.Item($adjEnd)
        if ($ep.Range.Information(12)) {
            $tbl2 = $ep.Range.Tables.Item(1)
            $total = $srcDoc.Paragraphs.Count
            for ($ti = $adjEnd; $ti -le $total; $ti++) {
                $tp = $srcDoc.Paragraphs.Item($ti)
                if (-not $tp.Range.Information(12)) { break }
                $ttbl2 = $tp.Range.Tables.Item(1)
                if ($ttbl2.Range.Start -ne $tbl2.Range.Start) { break }
                $adjEnd = $ti
            }
            Write-Output "  └ end 段$($b.end)在表格内，扩展到表尾段$adjEnd"
        }

        $sPos = $srcDoc.Paragraphs.Item($adjStart).Range.Start
        $ePos = $srcDoc.Paragraphs.Item($adjEnd).Range.End
        $rng = $srcDoc.Range($sPos, $ePos)
        $shapeCnt = $rng.InlineShapes.Count
        $rng.Copy()
        $find = $tplDoc.Content.Find
        $find.ClearFormatting(); $find.Text = $b.marker
        if ($find.Execute()) {
            # 关键修复：取锚点所在【整段】，在该段末尾插入，绝不切开标题
            # （$find.Parent 只是匹配到的文字，折叠到它的末尾会落在标题中间）
            $anchorPara = $find.Parent.Paragraphs.Item(1).Range
            $ins = $tplDoc.Range($anchorPara.End, $anchorPara.End)  # 标题段之后
            $startPos = $ins.Start
            $ins.Paste()
            $endPos = $ins.End
            Write-Output "  [$($b.marker)] 段$($b.start)-$($b.end) → 已粘贴（公式 $shapeCnt）"

            # ——— 自动套格式（仅作用于刚粘进来的范围）———
            if ($doFmt -and $endPos -gt $startPos) {
                try {
                    $pasted = $tplDoc.Range($startPos, $endPos)
                    $pasted.ParagraphFormat.LineSpacingRule = 1     # wdLineSpace1pt5 = 1.5倍行距
                    $pasted.Font.NameFarEast = "宋体"               # 中文宋体
                    $pasted.Font.NameAscii   = "Times New Roman"    # 西文新罗马
                    $pasted.Font.NameOther   = "Times New Roman"
                    $pasted.Font.Size        = 10.5                 # 五号字（正文）
                    Write-Output "    └ 已套格式：宋体/Times New Roman · 1.5倍行距 · 五号"
                } catch {
                    Write-Output "    └ [警告] 套格式失败（不影响内容）: $($_.Exception.Message)"
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
            # 从最后一个段落往前删（避免索引漂移）
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
    # 仅清理我们启动的 Word 进程（不影响用户正在编辑的文档）
    if ($wordPid) {
        try { Stop-Process -Id $wordPid -Force -ErrorAction Stop } catch {}
    }
}
