$ErrorActionPreference = 'Stop'
# Extract the original GLOBAL\ATTRIBUTES.BIN entry for vehicle-physics research.
# Run beside ZZDATA1.BIN. The archive is opened read-only.
# Directory hash9775379a; offset/size validated against supplied ZDIR.BIN.
$entries = @(
    @{ Source = 'ZZDATA1.BIN'; ArchiveSize = 340240384; Name = 'ATTRIBUTES.BIN'; Offset = 265320448; Size = 694976 }
)
$destination = Join-Path (Get-Location) 'vehicle-physics-samples'
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
