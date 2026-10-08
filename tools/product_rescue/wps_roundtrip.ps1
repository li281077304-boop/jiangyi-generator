param([Parameter(Mandatory=$true)][string]$Manifest, [Parameter(Mandatory=$true)][string]$OutputRoot)
$ErrorActionPreference = 'Stop'
$items = Get-Content -LiteralPath $Manifest -Raw -Encoding UTF8 | ConvertFrom-Json
New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
$records = [System.Collections.Generic.List[object]]::new()
$app = $null
try {
    $app = New-Object -ComObject KWPS.Application
    $app.Visible = $false
    $app.DisplayAlerts = 0
    foreach ($item in $items) {
        $saved = Join-Path $OutputRoot ($item.id + '-saved.docx')
        $pdf = Join-Path $OutputRoot ($item.id + '.pdf')
        $row = [ordered]@{ id=$item.id; source=$item.path; source_sha256=(Get-FileHash -LiteralPath $item.path -Algorithm SHA256).Hash; open=$false; saveas=$false; reopen=$false; pdf=$false; saved=$saved; pdf_path=$pdf; error=$null }
        $doc = $null
        try {
            $doc = $app.Documents.Open($item.path, $false, $false, $false)
            $row.open = $true
            $row.before = @{ paragraphs=$doc.Paragraphs.Count; tables=$doc.Tables.Count; inline_shapes=$doc.InlineShapes.Count; text_length=$doc.Content.Text.Length }
            $doc.SaveAs($saved, 16)
            $row.saveas = (Get-Item -LiteralPath $saved).Length -gt 0
            $doc.Close(0)
            $doc = $null
            $doc = $app.Documents.Open($saved, $false, $false, $false)
            $row.reopen = $true
            $row.after = @{ paragraphs=$doc.Paragraphs.Count; tables=$doc.Tables.Count; inline_shapes=$doc.InlineShapes.Count; text_length=$doc.Content.Text.Length }
            $doc.SaveAs($pdf, 17)
            $row.pdf = (Get-Item -LiteralPath $pdf).Length -gt 0
        } catch { $row.error = $_.Exception.ToString() }
        finally { if ($doc) { $doc.Close(0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc) } }
        $records.Add([pscustomobject]$row)
        ConvertTo-Json -InputObject @($records.ToArray()) -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputRoot 'wps_evidence.json') -Encoding UTF8
        Write-Output ($item.id + ': open=' + $row.open + ', reopen=' + $row.reopen + ', pdf=' + $row.pdf + ', error=' + $row.error)
    }
} finally { if ($app) { $app.Quit(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app) } }
