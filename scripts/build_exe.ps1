param(
  [string]$Name = "SenseisUpdater"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Error "Python launcher 'py' not found."
}

py -3 -m pip install --upgrade pip
py -3 -m pip install pyinstaller

# Clean previous
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue | Out-Null

# Build
py -3 -m PyInstaller --noconfirm --clean --onefile --name $Name --console `
  src/sensei_updater/app.py

Write-Host "EXE ready: dist\$Name.exe"