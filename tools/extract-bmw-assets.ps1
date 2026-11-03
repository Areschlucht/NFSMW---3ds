$ErrorActionPreference = 'Stop'
# Copy only the selected ranges; original ZZDATA1.BIN remains read-only.
$source = Get-Item 'ZZDATA1.BIN'
if ($source.Length -ne 340240384) { throw 'Unexpected archive size; stopping.' }
$destination = Join-Path (Get-Location) 'bmw-asset-samples'
New-Item -ItemType Directory -Force -Path $destination | Out-Null
$entries = @(
    @{ Name = 'CARS-TEXTURES.BIN'; Offset = 185245696; Size = 424832 },
    @{ Name = 'WHEELS-TEXTURES.BIN'; Offset = 189673472; Size = 344704 },
    @{ Name = 'BMWM3GTRE46-GEOMETRY.BIN'; Offset = 128100352; Size = 407680 },
    @{ Name = 'BMWM3GTRE46-TEXTURES.BIN'; Offset = 128518144; Size = 73152 }
)
foreach ($entry in $entries) {
    if (Test-Path (Join-Path $destination $entry.Name)) {
        throw "Destination already exists: $($entry.Name). Rename the old sample folder before retrying."
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
