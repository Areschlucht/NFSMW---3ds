$ErrorActionPreference = 'Stop'
# Run from the folder containing ZZDATA1.BIN. The archive is opened read-only.
# These are shared-file candidates, not yet confirmed to contain brake textures.
$source = Get-Item 'ZZDATA1.BIN'
if ($source.Length -ne 340240384) { throw 'Unexpected ZZDATA1.BIN size; stopping.' }
$destination = Join-Path (Get-Location) 'shared-texture-samples'
New-Item -ItemType Directory -Force -Path $destination | Out-Null
$entries = @(
    @{ Name = 'GLOBAL-GLOBALA.BUN'; Offset = 82796544; Size = 89588 },
    @{ Name = 'GLOBAL-GLOBALB.BUN'; Offset = 269469696; Size = 225776 },
    @{ Name = 'GLOBAL-GLOBALB.LZC'; Offset = 269697024; Size = 83654 }
)
foreach ($entry in $entries) {
    if (Test-Path (Join-Path $destination $entry.Name)) {
        throw "Destination already exists: $($entry.Name). Rename the existing sample folder before retrying."
    }
}
$inputFile = [System.IO.File]::OpenRead($source.FullName)
try {
    foreach ($entry in $entries) {
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
    }
} finally { $inputFile.Dispose() }
