$ErrorActionPreference = 'Stop'
# Original M3 vinyl/dynamic-texture inputs for paint-composition research.
# Run beside ZZDATA1.BIN; source opened read-only, existing outputs preserved.
# All ranges verified against supplied ZDIR. Three DYNTEX alternatives retained;
# no active-loader precedence or canonical livery is assumed from their order.
$entries = @(
    @{ Source = 'ZZDATA1.BIN'; ArchiveSize = 340240384; Name = 'BMWM3GTRE46-PREVINYL.BIN'; Offset = 128509952; Size = 8192 },
    @{ Source = 'ZZDATA1.BIN'; ArchiveSize = 340240384; Name = 'BMWM3GTRE46-VINYLS.BIN'; Offset = 128591872; Size = 2187392 },
    @{ Source = 'ZZDATA1.BIN'; ArchiveSize = 340240384; Name = 'GLOBAL-DYNTEX-266086400.BIN'; Offset = 266086400; Size = 1274240 },
    @{ Source = 'ZZDATA1.BIN'; ArchiveSize = 340240384; Name = 'GLOBAL-DYNTEX-279683072.BIN'; Offset = 279683072; Size = 1274240 },
    @{ Source = 'ZZDATA1.BIN'; ArchiveSize = 340240384; Name = 'GLOBAL-DYNTEX-299415552.BIN'; Offset = 299415552; Size = 1274240 }
)
$destination = Join-Path (Get-Location) 'vehicle-material-samples'
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
