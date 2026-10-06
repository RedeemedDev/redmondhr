#Requires -Version 3.0
<#
.SYNOPSIS
  Install RedmondHR Desktop (+ Start Menu) shortcut on Windows.
.DESCRIPTION
  Resolves Desktop via known folder / OneDrive Desktop when present
  (including "OneDrive - Redmond Movers\Desktop").

  Two launch modes:
  1) WSL (preferred for Adam): .lnk TargetPath = wsl.exe with
       -d <distro> --cd <linux-path> -- bash ./start-redmondhr.sh
     WorkingDirectory is %USERPROFILE% (never a UNC/WSL path — those
     break WScript.Shell CreateShortcut with ArgumentException).
  2) Native Windows: .lnk points at start-redmondhr.bat when the project
     lives on a real drive letter (not \\wsl.localhost\... / \\wsl$\...).

  Auto-detects \\wsl.localhost\<distro>\... and \\wsl$\<distro>\... UNC roots.
  Override with -WslDistro / -WslLinuxPath / -ForceWindows.
#>
[CmdletBinding()]
param(
  [switch]$NoStartMenu,
  [string]$ProjectRoot = $PSScriptRoot,
  [string]$WslDistro = '',
  [string]$WslLinuxPath = '',
  [switch]$ForceWindows,
  [switch]$ForceWsl
)

$ErrorActionPreference = 'Stop'

function Add-Candidate {
  param(
    [System.Collections.Generic.List[string]]$List,
    [string]$Path
  )
  if ([string]::IsNullOrWhiteSpace($Path)) { return }
  $full = [Environment]::ExpandEnvironmentVariables($Path.TrimEnd('\', '/'))
  if (-not $List.Contains($full)) {
    [void]$List.Add($full)
  }
}

function ConvertFrom-WslUnc {
  param([string]$UncPath)
  # \\wsl.localhost\Ubuntu\home\adam\...  or  \\wsl$\Ubuntu\home\adam\...
  # Also tolerate forward slashes from some shells.
  $n = $UncPath -replace '/', '\'
  $m = [regex]::Match(
    $n,
    '^[\\]{2}wsl(?:\.localhost|\$)\\([^\\]+)\\(.+)$',
    [System.Text.RegularExpressions.RegexOptions]::IgnoreCase
  )
  if (-not $m.Success) { return $null }
  $distro = $m.Groups[1].Value
  $rest = ($m.Groups[2].Value -replace '\\', '/').TrimEnd('/')
  if (-not $rest.StartsWith('/')) { $rest = '/' + $rest }
  return @{ Distro = $distro; LinuxPath = $rest }
}

function Resolve-WslExe {
  $cmd = Get-Command wsl.exe -ErrorAction SilentlyContinue
  if ($cmd -and $cmd.Source) { return $cmd.Source }
  foreach ($c in @(
      (Join-Path $env:SystemRoot 'System32\wsl.exe'),
      (Join-Path $env:SystemRoot 'Sysnative\wsl.exe')
    )) {
    if (Test-Path -LiteralPath $c) { return $c }
  }
  return 'wsl.exe'
}

# --- Resolve project root (may be UNC; do not cd there) ---
$root = $null
if (-not [string]::IsNullOrWhiteSpace($ProjectRoot)) {
  try {
    $root = (Resolve-Path -LiteralPath $ProjectRoot).Path
  } catch {
    # Resolve-Path can fail on some WSL UNC forms; keep the literal.
    $root = $ProjectRoot.TrimEnd('\', '/')
  }
}
if ([string]::IsNullOrWhiteSpace($root)) {
  Write-Error 'ProjectRoot is empty.'
  exit 1
}

$wslInfo = ConvertFrom-WslUnc $root
$useWsl = $false
$linuxPath = ''
$distro = ''

if ($ForceWindows -and $ForceWsl) {
  Write-Error 'Use only one of -ForceWindows / -ForceWsl.'
  exit 1
}

if (-not [string]::IsNullOrWhiteSpace($WslDistro) -or -not [string]::IsNullOrWhiteSpace($WslLinuxPath)) {
  if ([string]::IsNullOrWhiteSpace($WslDistro) -or [string]::IsNullOrWhiteSpace($WslLinuxPath)) {
    Write-Error 'When overriding WSL, pass both -WslDistro and -WslLinuxPath.'
    exit 1
  }
  $useWsl = $true
  $distro = $WslDistro
  $linuxPath = ($WslLinuxPath -replace '\\', '/').TrimEnd('/')
  if (-not $linuxPath.StartsWith('/')) { $linuxPath = '/' + $linuxPath }
} elseif ($ForceWsl) {
  if ($wslInfo) {
    $useWsl = $true
    $distro = $wslInfo.Distro
    $linuxPath = $wslInfo.LinuxPath
  } else {
    Write-Error '-ForceWsl set but ProjectRoot is not a WSL UNC path. Pass -WslDistro and -WslLinuxPath.'
    exit 1
  }
} elseif ($ForceWindows) {
  $useWsl = $false
} elseif ($wslInfo) {
  $useWsl = $true
  $distro = $wslInfo.Distro
  $linuxPath = $wslInfo.LinuxPath
}

$startBat = Join-Path $root 'start-redmondhr.bat'
$startShName = 'start-redmondhr.sh'

if (-not $useWsl) {
  if (-not (Test-Path -LiteralPath $startBat)) {
    if ($wslInfo) {
      Write-Error @"
start-redmondhr.bat not usable from WSL UNC, and Windows mode was forced/selected.
Project appears to be under WSL ($($wslInfo.Distro):$($wslInfo.LinuxPath)).
Re-run without -ForceWindows, or pass -WslDistro / -WslLinuxPath.
"@
    } else {
      Write-Error "start-redmondhr.bat not found at: $startBat"
    }
    exit 1
  }
}

# --- Resolve Desktop (OneDrive-aware) ---
$candidates = New-Object 'System.Collections.Generic.List[string]'

try {
  Add-Candidate $candidates ([Environment]::GetFolderPath('Desktop'))
} catch {}

try {
  $shellApp = New-Object -ComObject Shell.Application
  $deskFolder = $shellApp.NameSpace('shell:Desktop')
  if ($deskFolder -and $deskFolder.Self) {
    Add-Candidate $candidates $deskFolder.Self.Path
  }
} catch {}

if ($env:OneDriveCommercial) {
  Add-Candidate $candidates (Join-Path $env:OneDriveCommercial 'Desktop')
}
if ($env:OneDrive) {
  Add-Candidate $candidates (Join-Path $env:OneDrive 'Desktop')
}

Add-Candidate $candidates (Join-Path $env:USERPROFILE 'OneDrive - Redmond Movers\Desktop')

Get-ChildItem -Path $env:USERPROFILE -Directory -Filter 'OneDrive*' -ErrorAction SilentlyContinue |
  ForEach-Object { Add-Candidate $candidates (Join-Path $_.FullName 'Desktop') }

Add-Candidate $candidates (Join-Path $env:USERPROFILE 'Desktop')
Add-Candidate $candidates 'C:\Users\AdamRedmond\OneDrive - Redmond Movers\Desktop'

$desktop = $null
foreach ($c in $candidates) {
  if ($c -and (Test-Path -LiteralPath $c -PathType Container)) {
    $desktop = $c
    break
  }
}

if (-not $desktop) {
  Write-Host 'ERROR: Could not resolve a Desktop folder. Tried:'
  foreach ($c in $candidates) { Write-Host "  $c" }
  exit 1
}

Write-Host "Desktop: $desktop"

# WorkingDirectory must be a real Windows path — never UNC/WSL.
$workDir = $env:USERPROFILE
if ([string]::IsNullOrWhiteSpace($workDir) -or -not (Test-Path -LiteralPath $workDir)) {
  $workDir = Join-Path $env:SystemRoot 'System32'
}

function New-RedmondHrShortcut {
  param(
    [string]$LnkPath,
    [string]$Target,
    [string]$Arguments,
    [string]$WorkDir,
    [string]$Description
  )
  $ws = New-Object -ComObject WScript.Shell
  $sc = $ws.CreateShortcut($LnkPath)
  $sc.TargetPath = $Target
  if (-not [string]::IsNullOrWhiteSpace($Arguments)) {
    $sc.Arguments = $Arguments
  }
  $sc.WorkingDirectory = $WorkDir
  # 1 = Normal — console stays open; closing it stops RedmondHR (via start-redmondhr.sh EXIT trap)
  $sc.WindowStyle = 1
  $sc.Description = $Description
  $sc.IconLocation = 'shell32.dll,165'
  $sc.Save()
  Write-Host "Installed: $LnkPath"
}

$deskLnk = Join-Path $desktop 'RedmondHR.lnk'

if ($useWsl) {
  $wslExe = Resolve-WslExe
  # --cd sets the Linux cwd; script path is relative. No UNC on .lnk fields.
  $wslArgs = "-d $distro --cd `"$linuxPath`" -- bash ./$startShName"
  $desc = "Start RedmondHR via WSL ($distro)"
  Write-Host "Mode: WSL"
  Write-Host "  Distro: $distro"
  Write-Host "  Linux:  $linuxPath"
  Write-Host "  Target: $wslExe $wslArgs"
  Write-Host "  WorkDir: $workDir"
  New-RedmondHrShortcut -LnkPath $deskLnk -Target $wslExe -Arguments $wslArgs -WorkDir $workDir -Description $desc

  # Also drop a plain .bat on Desktop as a UNC-safe fallback (optional double-click).
  $deskBat = Join-Path $desktop 'RedmondHR.bat'
  $batBody = @"
@echo off
REM RedmondHR Desktop launcher (WSL) — WorkingDirectory not required.
REM Generated by install-desktop-shortcut.ps1
wsl.exe -d $distro --cd "$linuxPath" -- bash ./$startShName
"@
  Set-Content -LiteralPath $deskBat -Value $batBody -Encoding ASCII
  Write-Host "Installed: $deskBat (fallback)"

  if (-not $NoStartMenu) {
    $programs = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
    if (-not (Test-Path -LiteralPath $programs)) {
      New-Item -ItemType Directory -Path $programs -Force | Out-Null
    }
    $smLnk = Join-Path $programs 'RedmondHR.lnk'
    New-RedmondHrShortcut -LnkPath $smLnk -Target $wslExe -Arguments $wslArgs -WorkDir $workDir -Description $desc
  }
} else {
  Write-Host "Mode: Windows native"
  Write-Host "  Target: $startBat"
  Write-Host "  WorkDir: $root"
  New-RedmondHrShortcut -LnkPath $deskLnk -Target $startBat -Arguments '' -WorkDir $root -Description 'Start RedmondHR (local manager HR toolkit)'

  if (-not $NoStartMenu) {
    $programs = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
    if (-not (Test-Path -LiteralPath $programs)) {
      New-Item -ItemType Directory -Path $programs -Force | Out-Null
    }
    $smLnk = Join-Path $programs 'RedmondHR.lnk'
    New-RedmondHrShortcut -LnkPath $smLnk -Target $startBat -Arguments '' -WorkDir $root -Description 'Start RedmondHR (local manager HR toolkit)'
  }
}

Write-Host ''
Write-Host 'Double-click RedmondHR on your Desktop (or Start Menu) to launch.'
Write-Host 'A console window stays open — close it to stop RedmondHR.'
exit 0
