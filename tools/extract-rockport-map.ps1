$ErrorActionPreference = 'Stop'
# Extract only the identified original Rockport entries and a bounded stream
# prefix. The prefix is for format/index inspection, not a complete map file.
$entries = @(
    @{ Source = 'ZZDATA1.BIN'; ArchiveSize = 340240384; Name = 'L2RA.BUN'; Offset = 280958976; Size = 982848 },
    @{ Source = 'ZZDATA1.BIN'; ArchiveSize = 340240384; Name = 'TrackMaps.bin'; Offset = 281942016; Size = 16634816 },
    @{ Source = 'ZZDATA3.BIN'; ArchiveSize = 346253312; Name = 'STREAML2RA-first8MiB.BUN'; Offset = 131596288; Size = 8388608 }
)
$destination = Join-Path (Get-Location) 'rockport-map-samples'
foreach ($entry in $entries) {
    $source = Get-Item $entry.Source
    if ($source.Length -ne $entry.ArchiveSize) { throw "Unexpected size: $($entry.Source)" }
    if (Test-Path (Join-Path $destination $entry.Name)) { throw "Destination exists: $($entry.Name). Rename the old sample folder before retrying." }
}
New-Item -ItemType Directory -Force -Path $destination | Out-Null
foreach ($entry in $entries) {
    $source = Get-Item $entry.Source
    $inputFile = [System.IO.File]::OpenRead($source.FullName)
    try {
        $path = Join-Path $destination $entry.Name
        $outputFile = [System.IO.File]::Open($path, [System.IO.FileMode]::CreateNew)
        try {
            [void]$inputFile.Seek($entry.Offset, [System.IO.SeekOrigin]::Begin)
            $remaining = $entry.Size
            $buffer = New-Object byte[] 65536
            while ($remaining -gt 0) {
                $count = $inputFile.Read($buffer, 0, [Math]::Min($remaining, $buffer.Length))
                if ($count -eq 0) { throw 'Unexpected end of archive' }
                $outputFile.Write($buffer, 0, $count)
                $remaining -= $count
            }
        } finally { $outputFile.Dispose() }
        Write-Host "Created $path"
    } finally { $inputFile.Dispose() }
}
