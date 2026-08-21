$ErrorActionPreference = "Stop"
$src = [System.IO.Path]::GetFullPath($args[0])
$pdf = [System.IO.Path]::GetFullPath($args[1])
$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($src, $false, $true)
    # 17 = wdExportFormatPDF
    $doc.ExportAsFixedFormat($pdf, 17, $false, 0, 0, 0, 0, 0, $false, $false, 0, $true, $false, $false)
    $doc.Close($false)
    $doc = $null
    $word.Quit()
    $word = $null
    exit 0
}
catch {
    if ($doc -ne $null) { try { $doc.Close($false) } catch {} }
    if ($word -ne $null) { try { $word.Quit() } catch {} }
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
