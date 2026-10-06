# APPLY — RedmondHR Windows Desktop shortcut via WSL (2026-10-06)

> **Superseded for WindowStyle:** see `APPLY-lifecycle.md` — use
> `WindowStyle=1` (normal) so closing the console stops the server.

Adam applies via archive extract. Unpack
`redmondhr-files-wsl-shortcut-2026-10-06.tar.gz` over the project root
(relative paths), or copy the listed files from `/workspace/redmondhr`.

## Problem

- Project is under WSL UNC: `\\wsl.localhost\Ubuntu\home\adamredmond\workspace\redmondhr`
- Desktop is OneDrive: `C:\Users\AdamRedmond\OneDrive - Redmond Movers\Desktop`
- `install-desktop-shortcut.bat` / CMD: UNC paths not supported as current directory
- PowerShell `WScript.Shell` `.lnk`: `WorkingDirectory` / `TargetPath` cannot be UNC reliably (`ArgumentException`)

## Fix

Desktop **RedmondHR.lnk** (and optional **RedmondHR.bat**) runs:

```text
wsl.exe -d Ubuntu --cd /home/adamredmond/workspace/redmondhr -- bash ./start-redmondhr.sh
```

`WorkingDirectory` = `%USERPROFILE%` (never UNC). `start-redmondhr.sh` resolves its own `ROOT` from `BASH_SOURCE` and opens the Windows browser under WSL.

## Files in this batch

| Path | Action |
|------|--------|
| `install-desktop-shortcut.ps1` | **replace** — WSL UNC detect + flags; wsl.exe .lnk |
| `install-desktop-shortcut.bat` | **replace** — no `cd` to UNC; `--wsl` / force flags |
| `start-redmondhr.sh` | **replace** — Windows browser when under WSL |
| `README.md` | **replace** — Adam WSL + one-liner |
| `APPLY-wsl-shortcut.md` | **new** — this file |

## For Carl → Adam: PowerShell one-liner (run NOW)

Paste into **Windows PowerShell** (any folder):

```powershell
$d="$env:USERPROFILE\OneDrive - Redmond Movers\Desktop"; if(!(Test-Path $d)){$d=[Environment]::GetFolderPath('Desktop')}; $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'RedmondHR.lnk')); $s.TargetPath='wsl.exe'; $s.Arguments='-d Ubuntu --cd /home/adamredmond/workspace/redmondhr -- bash ./start-redmondhr.sh'; $s.WorkingDirectory=$env:USERPROFILE; $s.WindowStyle=1; $s.Description='Start RedmondHR (WSL Ubuntu)'; $s.IconLocation='shell32.dll,165'; $s.Save(); Write-Host "Installed:" $s.FullName
```

Ensure `.venv` exists inside WSL first (`python3 -m venv .venv && pip install -r requirements.txt`).

## After extract (installer)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu\home\adamredmond\workspace\redmondhr\install-desktop-shortcut.ps1" -WslDistro Ubuntu -WslLinuxPath /home/adamredmond/workspace/redmondhr
```

Or auto-detect UNC:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu\home\adamredmond\workspace\redmondhr\install-desktop-shortcut.ps1"
```

Do **not** push from the agent; Adam decides when to commit/push.
