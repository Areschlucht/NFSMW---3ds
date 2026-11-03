$ErrorActionPreference = 'Stop'
# Run from the folder containing ZZDATA1.BIN. Originals are opened read-only.
$destination = Join-Path (Get-Location) 'asset-samples'
New-Item -ItemType Directory -Force -Path $destination | Out-Null
$source = Get-Item 'ZZDATA1.BIN'
if ($source.Length -ne 340240384) { throw 'Unexpected ZZDATA1.BIN size; stopping.' }
$entries = @(
    @{ Name = 'brakes-geometry.bin'; Offset = 130781184; Size = 6080 },
    @{ Name = 'english-textonly.bin'; Offset = 274601984; Size = 212136 }
)
$inputFile = [System.IO.File]::OpenRead($source.FullName)
try {
    foreach ($entry in $entries) {
        $path = Join-Path $destination $entry.Name
        # CreateNew prevents overwriting any existing user file.
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
