param(
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$source = "C:\Users\Yunus\.codex\visualizations\2026\07\10\019f4e12-9bbf-7000-949a-019b80f60bdd\phase8_highway_sequence_private_sources_r1\current_tsmis_excel\highway_sequence_route_010.xlsx"
$expectedBytes = 563703
$expectedSha256 = "5ada88f251d3e2a32aacafef1410ec877f403ea7405cfcd1d2b702fff75d0987"
$addresses = @("I1299", "I1300", "I1301", "I1302")

$item = Get-Item -LiteralPath $source
$sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash.ToLowerInvariant()
if ($item.Length -ne $expectedBytes -or $sha256 -ne $expectedSha256) {
    throw "Frozen route-010 source identity changed: $($item.Length)/$sha256"
}

function Convert-CellValue([object]$value) {
    $text = if ($null -eq $value) { "" } else { [string]$value }
    $codepoints = @($text.ToCharArray() | ForEach-Object { [int]$_ })
    return [ordered]@{
        text = $text
        codepoints = $codepoints
    }
}

$excel = $null
$book = $null
$sheet = $null
try {
    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.AskToUpdateLinks = $false
    $excel.AutomationSecurity = 3
    $book = $excel.Workbooks.Open($source, 0, $true)
    $sheet = $book.Worksheets.Item("Highway Locations")
    $cells = @()
    foreach ($address in $addresses) {
        $cell = $sheet.Range($address)
        $cells += [ordered]@{
            address = $address
            value2 = Convert-CellValue $cell.Value2
            formula = Convert-CellValue $cell.Formula
            display_text = Convert-CellValue $cell.Text
        }
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($cell)
    }
    $result = [ordered]@{
        audit = "Highway Sequence installed-Excel OOXML escape probe"
        source = [ordered]@{
            member = "highway_sequence_route_010.xlsx"
            bytes = $item.Length
            sha256 = $sha256
        }
        excel_version = [string]$excel.Version
        workbook_opened_read_only = [bool]$book.ReadOnly
        cells = $cells
        invariants = [ordered]@{
            cell_count_4 = $cells.Count -eq 4
            all_value2_end_crlf = @($cells | Where-Object {
                $cp = $_.value2.codepoints
                $cp.Count -lt 2 -or $cp[-2] -ne 13 -or $cp[-1] -ne 10
            }).Count -eq 0
            value_formula_display_exact = @($cells | Where-Object {
                $_.value2.text -cne $_.formula.text -or
                $_.value2.text -cne $_.display_text.text
            }).Count -eq 0
        }
    }
    if (@($result.invariants.Values | Where-Object { -not $_ }).Count -ne 0) {
        throw "Installed-Excel escape invariants failed"
    }
    $json = $result | ConvertTo-Json -Depth 8
    if ($OutputPath) {
        $parent = Split-Path -Parent $OutputPath
        if ($parent) {
            [IO.Directory]::CreateDirectory($parent) | Out-Null
        }
        [IO.File]::WriteAllText($OutputPath, $json + "`n", [Text.UTF8Encoding]::new($false))
    }
    $json
}
finally {
    if ($book -ne $null) {
        try { $book.Close($false) } catch {}
    }
    if ($excel -ne $null) {
        try { $excel.Quit() } catch {}
    }
    if ($sheet -ne $null) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($sheet) }
    if ($book -ne $null) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($book) }
    if ($excel -ne $null) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($excel) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
