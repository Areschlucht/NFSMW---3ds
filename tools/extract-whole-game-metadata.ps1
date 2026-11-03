param(
    [string]$GameDirectory = (Get-Location).Path,
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_.-]*$')]
    [string]$Destination = 'whole-game-metadata',
    [switch]$SelfTest
)
$ErrorActionPreference = 'Stop'
$extractor = Join-Path $PSScriptRoot 'extract-original-assets.ps1'
if (-not (Test-Path -LiteralPath $extractor -PathType Leaf)) {
    throw 'Keep extract-original-assets.ps1 beside this script.'
}
if ($SelfTest) { & $extractor -SelfTest; return }
$root = (Resolve-Path -LiteralPath $GameDirectory).Path
$outputPath = Join-Path $root $Destination
if (Test-Path -LiteralPath (Join-Path $outputPath 'disc-file-list.json')) {
    throw 'The output manifest already exists. Choose a new Destination.'
}
$entries = @(
    'GLOBAL\GAMEPLAY.BIN',
    'SOUND\PFData\MW_Mus_1.mpf',
    'SOUND\PFData\MW_Mus_2.mpf',
    'SOUND\PFData\MW_Mus_3.mpf',
    'SOUND\PFData\MW_Mus_4.mpf',
    'SOUND\PFData\MW_Music.mpf',
    'TRACKS\PRECULLERBOOBOOSCRIPT.HOO'
)
# The existing extractor validates the exact USA ZDIR hash, every indexed range,
# source archive size and output collision BEFORE opening output files. It uses
# OpenRead for game archives and retains BOTH matching GAMEPLAY records.
Push-Location -LiteralPath $root
try {
    & $extractor -Entries $entries -Destination $Destination
    $listing = @()
    # List only known game media folders and named root inputs. Do not recurse
    # into the user's other folders or follow junctions/symbolic links.
    foreach ($file in Get-ChildItem -LiteralPath $root -File) {
        if (($file.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { continue }
        if ($file.Name -match '^(?i:ZDIR\.BIN|ZZDATA[0-3]\.BIN|SPEED\.DOL|SPEED\.DDF|OPENING\.BNR)$') {
            $listing += [pscustomobject]@{ Path=$file.Name; Bytes=$file.Length }
        }
    }
    $queue = New-Object 'System.Collections.Generic.Queue[string]'
    foreach ($family in @('MOVIES','SOUND','CARS','FRONTEND','GLOBAL','TRACKS','LANGUAGES')) {
        $folder = Join-Path $root $family
        if (Test-Path -LiteralPath $folder -PathType Container) {
            $item = Get-Item -LiteralPath $folder
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) { $queue.Enqueue($item.FullName) }
        }
    }
    while ($queue.Count -gt 0) {
        $folder = $queue.Dequeue()
        foreach ($item in Get-ChildItem -LiteralPath $folder) {
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { continue }
            if ($item.PSIsContainer) { $queue.Enqueue($item.FullName); continue }
            $relative = $item.FullName.Substring($root.TrimEnd('\').Length).TrimStart('\')
            $listing += [pscustomobject]@{ Path=$relative; Bytes=$item.Length }
        }
    }
    # Only relative game paths and byte sizes; no personal absolute path or
    # contents of movie/audio files are added to this listing.
    ConvertTo-Json -InputObject @($listing | Sort-Object Path) -Depth 4 |
        Set-Content -LiteralPath (Join-Path $outputPath 'disc-file-list.json') -Encoding UTF8
    Write-Host 'Upload the small files and both JSON manifests from the output folder.'
} finally { Pop-Location }
