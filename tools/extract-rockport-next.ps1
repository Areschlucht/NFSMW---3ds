$ErrorActionPreference = 'Stop'
# Extract a larger shared-model prefix and the next available world-sector ranges.
# Reads ZZDATA3.BIN without modifying it. Each output is below 32 MiB.
# The prefix may end inside a chunk; the host reader accepts complete chunks only.
# Ranges come from the supplied L2RA.BUN 92-byte streaming records.
# These are research samples, not standalone playable map files.
# L2RA SHA-256: 73d4a98efcd366e6dc1e13a3fdc1f1494e8763edac05b7f911dc66b62c2c072d
$entries = @(
    @{ Source = 'ZZDATA3.BIN'; ArchiveSize = 346253312; Name = 'STREAML2RA-first24MiB.BUN'; Offset = 131596288; Size = 25165824 },
    @{ Source = 'ZZDATA3.BIN'; ArchiveSize = 346253312; Name = 'STREAML2RA-sectors161-176.BUN'; Offset = 158822400; Size = 2421088 },
    @{ Source = 'ZZDATA3.BIN'; ArchiveSize = 346253312; Name = 'STREAML2RA-sectors1161-1176.BUN'; Offset = 187881472; Size = 969408 }
)
$destination = Join-Path (Get-Location) 'rockport-next-samples'
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
