param(
    [string]$GameDirectory = (Get-Location).Path,
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_.-]*$')]
    [string]$Destination = 'nfsmw-remaining-game-files',
    [ValidateSet(0,1,2,3)][int[]]$Archives = @(1,0,2,3)
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath $GameDirectory).Path
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    throw 'GameDirectory must be the FOLDER containing ZDIR.BIN and ZZDATA*.BIN.'
}
if (@($Archives | Select-Object -Unique).Count -ne $Archives.Count -or $Archives.Count -eq 0) {
    throw 'Request each archive once.'
}
$index = Join-Path $root 'ZDIR.BIN'
$zdirSha = 'd5726a00d086edb5f8a47ff4bffa4715f84b44441987fd323141a6dfaf1ba333'
if ((Get-FileHash -LiteralPath $index -Algorithm SHA256).Hash.ToLowerInvariant() -ne $zdirSha) {
    throw 'ZDIR.BIN differs from the supplied USA directory; no output written.'
}
$sizes = @(315254784,340240384,330981376,346253312)
foreach ($archive in $Archives) {
    $source = Get-Item -LiteralPath (Join-Path $root ('ZZDATA{0}.BIN' -f $archive))
    if ($source.PSIsContainer -or $source.Length -ne $sizes[$archive]) {
        throw "Unexpected source size: $($source.Name). No output written."
    }
}
$outputPath = Join-Path $root $Destination
if (Test-Path -LiteralPath $outputPath) {
    throw 'Destination already exists. Keep its files; use -Destination with a new folder name.'
}
[void][IO.Directory]::CreateDirectory($outputPath)
[byte[]]$buffer = New-Object byte[] 1048576
[int64]$partLimit = 28 * 1048576
function Hex-Sha([byte[]]$Hash) { return ([BitConverter]::ToString($Hash)).Replace('-','').ToLowerInvariant() }
foreach ($archive in $Archives) {
    $sourceName = 'ZZDATA{0}.BIN' -f $archive
    $sourcePath = Join-Path $root $sourceName
    $inputStream = [IO.File]::OpenRead($sourcePath)
    $wholeHash = [Security.Cryptography.SHA256]::Create()
    $parts = @()
    [int64]$offset = 0
    [int]$partIndex = 0
    try {
        while ($offset -lt $sizes[$archive]) {
            $name = '{0}.part{1:D2}.bin' -f $sourceName,$partIndex
            $target = Join-Path $outputPath $name
            $outputStream = [IO.File]::Open($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            $partHash = [Security.Cryptography.SHA256]::Create()
            [int64]$wanted = [Math]::Min($partLimit,[int64]($sizes[$archive]-$offset))
            [int64]$written = 0
            try {
                while ($written -lt $wanted) {
                    [int]$request = [Math]::Min([int64]$buffer.Length,$wanted-$written)
                    [int]$read = $inputStream.Read($buffer,0,$request)
                    if ($read -le 0) { throw 'Unexpected end of original archive; keep error text.' }
                    $outputStream.Write($buffer,0,$read)
                    [void]$partHash.TransformBlock($buffer,0,$read,$buffer,0)
                    [void]$wholeHash.TransformBlock($buffer,0,$read,$buffer,0)
                    $written += $read
                }
                [void]$partHash.TransformFinalBlock([byte[]]@(),0,0)
                $partSha = Hex-Sha $partHash.Hash
            } finally { $outputStream.Dispose(); $partHash.Dispose() }
            $parts += [pscustomobject]@{ File=$name; Offset=$offset; Bytes=$written; SHA256=$partSha }
            Write-Host ('Ready: {0} ({1:N1} MiB)' -f $name,($written/1048576))
            $offset += $written
            $partIndex++
        }
        if ($inputStream.ReadByte() -ne -1) { throw 'Original archive changed length during collection.' }
        [void]$wholeHash.TransformFinalBlock([byte[]]@(),0,0)
        $manifest = [pscustomobject]@{
            Schema=1; Source=$sourceName; Bytes=$offset; SHA256=(Hex-Sha $wholeHash.Hash)
            ZdirSHA256=$zdirSha; PartBytes=$partLimit; Parts=$parts
        }
        ConvertTo-Json -InputObject $manifest -Depth 5 |
            Set-Content -LiteralPath (Join-Path $outputPath ($sourceName+'.parts.json')) -Encoding UTF8
    } finally { $inputStream.Dispose(); $wholeHash.Dispose() }
}
Write-Host 'Finished. Upload the .parts.json manifests and .bin pieces in small batches.'
Write-Host 'Priority: all ZZDATA1 pieces, then ZZDATA0, then ZZDATA2, then ZZDATA3.'
Write-Host 'Do not combine them into one huge ZIP. Originals were opened read-only.'
