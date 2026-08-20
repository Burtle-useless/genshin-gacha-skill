# Extract the newest Genshin wish-history URL from the game's web cache.
# The game holds data_2 with an exclusive lock for the whole session, so a
# direct read usually fails; we then self-elevate and copy via a VSS snapshot.
# ASCII only on purpose: a BOM-less UTF-8 .ps1 gets misread as CP950 by PS 5.1.
param(
    [switch]$VssOnly,
    [string]$Src,
    [string]$Dst
)

$ErrorActionPreference = 'Stop'

# --- elevated worker branch -------------------------------------------------
if ($VssOnly) {
    # The elevated child has no console we can read, so everything goes to a log.
    $logFile = Join-Path (Split-Path $Dst -Parent) 'vss.log'
    $isAdmin = ([Security.Principal.WindowsPrincipal] `
        [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole('Administrators')
    $lines = @("elevated=$isAdmin", "src=$Src", "dst=$Dst")
    if (Test-Path $Dst) { Remove-Item $Dst -Force }
    $lines += (& esentutl.exe /y $Src /vss /d $Dst 2>&1 | Out-String)
    $code = $LASTEXITCODE
    $lines += "esentutl_exit=$code"
    Set-Content -Path $logFile -Value $lines -Encoding ascii
    exit $code
}

# --- locate the game --------------------------------------------------------
$outDir = Join-Path $env:LOCALAPPDATA 'genshin-gacha'
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }

$logRoot = Join-Path $env:USERPROFILE 'AppData\LocalLow\miHoYo'
$log = Get-ChildItem $logRoot -Directory -ErrorAction SilentlyContinue |
    ForEach-Object { Join-Path $_.FullName 'output_log.txt' } |
    Where-Object { Test-Path $_ } |
    Sort-Object { (Get-Item $_).LastWriteTime } |
    Select-Object -Last 1

if (-not $log) { Write-Output 'ERROR: NO_LOG - game log not found, has the game ever run?'; exit 1 }

$hit = Select-String -Path $log -Pattern '([A-Za-z]:[\\/][^\r\n:*?"<>|]*?(?:GenshinImpact|YuanShen)_Data)' |
    Select-Object -Last 1
if (-not $hit) { Write-Output 'ERROR: NO_LOG - install path not found in log'; exit 1 }

$gameData = $hit.Matches[0].Groups[1].Value -replace '/', '\'
$cacheRoot = Join-Path $gameData 'webCaches'
if (-not (Test-Path $cacheRoot)) { Write-Output "ERROR: NO_LOG - webCaches missing under $gameData"; exit 1 }

# Cache dirs are named by version (2.54.0.0); newest wins. Fall back to the
# root itself for older layouts that had no version subfolder.
$verDir = Get-ChildItem $cacheRoot -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d+(\.\d+)+$' } |
    Sort-Object { [version]$_.Name } |
    Select-Object -Last 1
$cacheDir = if ($verDir) { $verDir.FullName } else { $cacheRoot }

$data2 = Join-Path $cacheDir 'Cache\Cache_Data\data_2'
if (-not (Test-Path $data2)) { Write-Output "ERROR: NO_URL - cache file missing: $data2"; exit 1 }

# --- read the cache, elevating only if we have to ---------------------------
$bytes = $null
try {
    $fs = [System.IO.File]::Open($data2, 'Open', 'Read', 'ReadWrite')
    try {
        $ms = New-Object System.IO.MemoryStream
        $fs.CopyTo($ms)
        $bytes = $ms.ToArray()
        $ms.Close()
    } finally { $fs.Close() }
} catch {
    Write-Output 'INFO: cache is locked by the running game, elevating for a VSS copy...'
    $tmp = Join-Path $outDir 'data_2.bin'
    # One quoted string, not an array: Start-Process joins array elements with
    # spaces without quoting them, which shreds paths like "Genshin Impact game".
    # not $args either: that is an automatic variable.
    $psArgs = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -VssOnly -Src "{1}" -Dst "{2}"' `
        -f $PSCommandPath, $data2, $tmp
    try {
        $p = Start-Process powershell -Verb RunAs -Wait -PassThru -ArgumentList $psArgs
    } catch {
        Write-Output 'ERROR: LOCKED_NO_ADMIN - UAC declined; close the game and retry'
        exit 1
    }
    if ($p.ExitCode -ne 0 -or -not (Test-Path $tmp)) {
        Write-Output "ERROR: LOCKED_NO_ADMIN - VSS copy failed (exit $($p.ExitCode)); close the game and retry"
        exit 1
    }
    $bytes = [System.IO.File]::ReadAllBytes($tmp)
    Remove-Item $tmp -Force -ErrorAction SilentlyContinue
}

# --- pull the URL out -------------------------------------------------------
# Chrome's cache stores the request URL as plain ASCII between binary records,
# so a byte-wise ASCII decode is enough; no need to parse the cache format.
$text = [System.Text.Encoding]::ASCII.GetString($bytes)
$rx = [regex]'https://[^\x00-\x1f"'']*getGachaLog[^\x00-\x1f"'']*'
$hits = $rx.Matches($text)
if ($hits.Count -eq 0) {
    Write-Output 'ERROR: NO_URL - no wish URL in cache; open the wish history page in-game once, then retry'
    exit 1
}

$url = $hits[$hits.Count - 1].Value
$urlFile = Join-Path $outDir 'url.txt'
Set-Content -Path $urlFile -Value $url -Encoding ascii
try { Set-Clipboard -Value $url } catch { }

Write-Output "OK: found $($hits.Count) cached requests, using the newest"
Write-Output "SAVED: $urlFile"
Write-Output $url
