# Install this skill for Claude Code and/or Codex CLI by creating a directory
# junction from the agent's skills folder to this repo.
#
# Junction (not symlink) on purpose: symlinks need admin or Developer Mode,
# junctions do not. One source of truth, so `git pull` updates every agent.
#
# ASCII only: a BOM-less UTF-8 .ps1 gets misread as CP950 by PowerShell 5.1.
param(
    [switch]$Claude,
    [switch]$Codex,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$source = $PSScriptRoot
$name = Split-Path $source -Leaf

# No target given: install for whichever agents are already set up.
if (-not $Claude -and -not $Codex) {
    $Claude = Test-Path (Join-Path $HOME '.claude')
    $Codex = Test-Path (Join-Path $HOME '.codex')
    if (-not $Claude -and -not $Codex) {
        Write-Output 'Neither ~/.claude nor ~/.codex exists. Pass -Claude or -Codex to force.'
        exit 1
    }
}

$targets = @()
if ($Claude) { $targets += Join-Path $HOME '.claude\skills' }
if ($Codex) { $targets += Join-Path $HOME '.codex\skills' }

foreach ($root in $targets) {
    if (-not (Test-Path $root)) { New-Item -ItemType Directory -Path $root -Force | Out-Null }
    $link = Join-Path $root $name

    if ($link -eq $source) {
        Write-Output "SKIP  $link (this is the source itself)"
        continue
    }
    if (Test-Path $link) {
        if (-not $Force) {
            Write-Output "SKIP  $link already exists (use -Force to replace)"
            continue
        }
        $item = Get-Item $link -Force
        if ($item.LinkType) { $item.Delete() } else { Remove-Item $link -Recurse -Force }
    }

    New-Item -ItemType Junction -Path $link -Target $source | Out-Null
    Write-Output "LINK  $link -> $source"
}

Write-Output ''
Write-Output "Set the display language in $source\data\config.json (lang: zh or en)."
Write-Output 'Python deps: python -m pip install requests pillow'
