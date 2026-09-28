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
        $para = $doc.Paragraphs.Item($i)
        $t = $para.Range.Text
        # v1.0: 去掉 Word XML 控制字符编码（如 _x0007_、_x001F_ 等）
        $t = $t -replace '_x[0-9A-Fa-f]{4}_', ''
        # 去掉所有控制字符（\r \n \t \f \v \a \b \0 及 0x00-0x1F）
        $t = $t -replace "[\u0000-\u001F]", ' '
        $t = $t.Trim()
        # flash: 检测段落是否含图片/图形（InlineShapes 含内嵌图片；Shapes 含浮动图形）
        $hasImg = 0
        try {
            if ($para.Range.InlineShapes.Count -gt 0) { $hasImg = 1 }
            else {
                foreach ($shp in $doc.Shapes) {
                    if ($shp.Anchor.Paragraph.Index -eq $i) { $hasImg = 1; break }
                }
            }
        } catch { }
        $lines.Add("$i`t$t`t$hasImg")
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
