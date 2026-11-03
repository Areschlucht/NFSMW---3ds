$ErrorActionPreference = 'Stop'
# Remaining original STREAML2RA.BUN bytes for whole-map/collision research.
# Run beside ZZDATA3.BIN. Read-only; existing outputs are never overwritten.
# The first24MiB file is already supplied. These three parts complete it.
# ZDIR hash4b91a993: archive3 base131596288 length109279744, verified.
# Individual parts are below32MiB and are not standalone asset packages.
$entries = @(
    @{ Source = 'ZZDATA3.BIN'; ArchiveSize = 346253312; Name = 'STREAML2RA-24-52MiB.bin'; Offset = 156762112; Size = 29360128 },
    @{ Source = 'ZZDATA3.BIN'; ArchiveSize = 346253312; Name = 'STREAML2RA-52-80MiB.bin'; Offset = 186122240; Size = 29360128 },
    @{ Source = 'ZZDATA3.BIN'; ArchiveSize = 346253312; Name = 'STREAML2RA-80MiB-end.bin'; Offset = 215482368; Size = 25393664 }
)
$destination = Join-Path (Get-Location) 'rockport-stream-remainder'
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
