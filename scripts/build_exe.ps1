param(
  [string]$Name = "SenseisUpdater"
)

$ErrorActionPreference = "Stop"

# --- Check Python launcher ---
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Error "Python launcher 'py' not found. Install Python 3 and ensure 'py' is on PATH."
}

# --- Ensure build tools ---
py -3 -m pip install --upgrade pip
py -3 -m pip install pyinstaller

# --- Clean previous outputs ---
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue | Out-Null

# --- Create a small entry script that calls your package main() ---
New-Item -ItemType Directory -Force -Path build | Out-Null

$entryCode = @"
from sensei_updater.__main__ import run

if __name__ == "__main__":
    run()
"@

$entryPath = Join-Path $PWD "build\entry.py"
Set-Content -Path $entryPath -Value $entryCode -Encoding UTF8

# --- Build with PyInstaller ---
py -3 -m PyInstaller --noconfirm --clean --onefile --console `
  --name $Name `
  --paths src `
  $entryPath

Write-Host "EXE ready: dist\$Name.exe"