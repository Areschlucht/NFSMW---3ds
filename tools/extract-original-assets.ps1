param(
    [string[]]$Entries = @(
        'FRONTEND\FRONTB.LZC',
        'FRONTEND\FRONTB_VM_NGC.LZC',
        'GLOBAL\FE_ATTRIB.BIN',
        'GLOBAL\GLOBALMEMORYFILE.BIN',
        'GLOBAL\GLOBALB_VM_NGC.LZC'
    ),
    [string]$Destination = 'original-asset-samples',
    [ValidateRange(1,28)][int]$PartMiB = 28,
    [switch]$SelfTest
)
$ErrorActionPreference = 'Stop'
# Run beside the original ZDIR.BIN and ZZDATA*.BIN files. Sources are read-only.
# Original entry names are hashed, never executed or used as output paths.
function Get-EntryHash([string]$Name) {
    [UInt64]$value = 4294967295
    foreach ($b in [Text.Encoding]::ASCII.GetBytes($Name.ToUpperInvariant())) {
        $value = (($value * 33 + $b) -band [UInt64]4294967295)
    }
    return [UInt32]$value
}
$known = @(
    @{ Name = 'GLOBAL\ATTRIBUTES.BIN'; Hash = [UInt32]2541041562 },
    @{ Name = 'TRACKS\STREAML2RA.BUN'; Hash = [UInt32]1267837331 },
    @{ Name = 'CARS\BMWM3GTRE46\PREVINYL.BIN'; Hash = [UInt32]559227746 },
    @{ Name = 'CARS\BMWM3GTRE46\VINYLS.BIN'; Hash = [UInt32]331189230 }
)
foreach ($case in $known) {
    if ((Get-EntryHash $case.Name) -ne $case.Hash) { throw "Entry hash self-test failed: $($case.Name)" }
}
if ($SelfTest) { Write-Host 'Four original entry-hash checks passed.'; return }
$directory = Get-Item 'ZDIR.BIN'
if ((Get-FileHash -LiteralPath $directory.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'd5726a00d086edb5f8a47ff4bffa4715f84b44441987fd323141a6dfaf1ba333') {
    throw 'ZDIR.BIN differs from the supplied USA directory; stopping before extraction.'
}
$raw = [IO.File]::ReadAllBytes($directory.FullName)
if ($raw.Length -eq 0 -or $raw.Length % 24 -ne 0) { throw 'Malformed directory length.' }
$archiveSizes = @(315254784,340240384,330981376,346253312)
$bases = @(0,153933,320066,481678)
$records = @()
[UInt64]$previousHash = 0
for ($at = 0; $at -lt $raw.Length; $at += 24) {
    $key = [BitConverter]::ToUInt32($raw,$at)
    $archive = [BitConverter]::ToUInt32($raw,$at+4)
    [UInt64]$sector = [BitConverter]::ToUInt32($raw,$at+8)
    $combined = [BitConverter]::ToUInt32($raw,$at+12)
    [UInt64]$size = [BitConverter]::ToUInt32($raw,$at+16)
    [UInt64]$offset = $sector * 2048
    if ($key -lt $previousHash -or $archive -gt 3) { throw 'Invalid sorted directory/selector.' }
    if ($combined -ne $sector+$bases[$archive] -or $offset+$size -gt $archiveSizes[$archive]) { throw 'Invalid indexed byte range.' }
    $records += [pscustomobject]@{ Hash=$key; Archive=$archive; Offset=$offset; Size=$size; DirectoryOffset=$at }
    $previousHash = $key
}
$jobs = @()
foreach ($entry in $Entries) {
    if ($entry -notmatch '^[\x20-\x7E]+$') { throw 'Original entry name must be ASCII.' }
    $key = Get-EntryHash $entry
    $matches = @($records | Where-Object { $_.Hash -eq $key })
    if ($matches.Count -eq 0) { throw "Entry is absent from the directory: $entry" }
    # Keep every hash match; duplicates are not assumed identical or canonical.
    foreach ($record in $matches) {
        $leaf = [Regex]::Replace($entry.ToUpperInvariant().Replace([char]92,[char]45),'[^A-Z0-9_.-]','_')
        if ($matches.Count -gt 1) {
            $extension = [IO.Path]::GetExtension($leaf)
            $leaf = [IO.Path]::GetFileNameWithoutExtension($leaf)+'-at'+$record.Offset+$extension
        }
        [UInt64]$done = 0
        $part = 0
        do {
            [UInt64]$size = [Math]::Min([UInt64]($PartMiB*1048576),[UInt64]($record.Size-$done))
            $name = $leaf
            if ($record.Size -gt $PartMiB*1048576) { $name += ('-part{0:D2}.bin' -f $part) }
            $jobs += [pscustomobject]@{ Entry=$entry; Hash=('{0:x8}' -f $key); Archive=$record.Archive; Name=$name; Offset=($record.Offset+$done); Size=$size; EntrySize=$record.Size; PartOffset=$done; DirectoryOffset=$record.DirectoryOffset }
            $done += $size; $part++
        } while ($done -lt $record.Size)
    }
}
if ($jobs.Count -eq 0) { throw 'No requested entries.' }
$destinationPath = [IO.Path]::GetFullPath((Join-Path (Get-Location) $Destination))
$names = @{}
foreach ($job in $jobs) {
    $source = Get-Item ('ZZDATA{0}.BIN' -f $job.Archive)
    if ($source.Length -ne $archiveSizes[$job.Archive]) { throw "Unexpected source size: $($source.Name)" }
    if ($names.ContainsKey($job.Name)) { throw 'Duplicate output name; request each original entry only once.' }
    $names[$job.Name] = $true
    if (Test-Path -LiteralPath (Join-Path $destinationPath $job.Name)) { throw "Output already exists: $($job.Name). Rename the old output folder before retrying." }
}
New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
$manifest = @()
foreach ($job in $jobs) {
    $source = Get-Item ('ZZDATA{0}.BIN' -f $job.Archive)
    $inputFile = [IO.File]::OpenRead($source.FullName)
    $path = Join-Path $destinationPath $job.Name
    try {
        $outputFile = [IO.File]::Open($path,[IO.FileMode]::CreateNew)
        try {
            [void]$inputFile.Seek([Int64]$job.Offset,[IO.SeekOrigin]::Begin)
            [UInt64]$remaining = $job.Size
            $buffer = New-Object byte[] 65536
            while ($remaining -gt 0) {
                $count = $inputFile.Read($buffer,0,[int][Math]::Min($remaining,[UInt64]$buffer.Length))
                if ($count -eq 0) { throw 'Unexpected end of source archive.' }
                $outputFile.Write($buffer,0,$count); $remaining -= $count
            }
        } finally { $outputFile.Dispose() }
    } finally { $inputFile.Dispose() }
    $manifest += [pscustomobject]@{ Entry=$job.Entry; EntryHash=$job.Hash; Source=$source.Name; ArchiveOffset=$job.Offset; Bytes=$job.Size; EntryBytes=$job.EntrySize; PartOffset=$job.PartOffset; DirectoryRecordOffset=$job.DirectoryOffset; Output=$job.Name; SHA256=(Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
    Write-Host "Created $path"
}
$manifestPath = Join-Path $destinationPath ('manifest-{0}.json' -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
ConvertTo-Json -InputObject @($manifest) -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Host "Manifest: $manifestPath"
