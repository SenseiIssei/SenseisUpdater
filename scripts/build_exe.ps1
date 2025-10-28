param(
  [string]$Name = "SenseisUpdater"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Error "Python launcher 'py' not found. Install Python 3 and ensure 'py' is on PATH."
}

try { Get-Process -Name $Name -ErrorAction Stop | Stop-Process -Force } catch {}
try { taskkill /IM "$Name.exe" /F | Out-Null } catch {}

py -3 -m pip install --upgrade pip
py -3 -m pip install --upgrade pyinstaller PySide6 shiboken6

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue | Out-Null
New-Item -ItemType Directory -Force -Path build | Out-Null

$entryCode = @"
from sensei_updater.__main__ import run
if __name__ == "__main__":
    run()
"@
$entryPath = Join-Path $PWD "build\entry.py"
Set-Content -Path $entryPath -Value $entryCode -Encoding UTF8

$manifestPath = Join-Path $PWD "build\app.manifest"
$manifest = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <assemblyIdentity version="1.0.0.0" processorArchitecture="*" name="$Name" type="win32"/>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false"/>
      </requestedPrivileges>
    </security>
  </trustInfo>
  <dependency>
    <dependentAssembly>
      <assemblyIdentity type="win32" name="Microsoft.VC90.CRT" version="9.0.21022.8" processorArchitecture="*" publicKeyToken="1fc8b3b9a1e18e3b"/>
    </dependentAssembly>
  </dependency>
</assembly>
"@
Set-Content -Path $manifestPath -Value $manifest -Encoding UTF8

$qss = "src\sensei_updater\ui\styles.qss"

py -3 -m PyInstaller `
  --noconfirm --clean --onefile --windowed `
  --name $Name `
  --paths src `
  --uac-admin `
  --manifest $manifestPath `
  --collect-all PySide6 `
  --hidden-import shiboken6 `
  --hidden-import sensei_updater.ui.pages.apps_page `
  --hidden-import sensei_updater.ui.pages.drivers_page `
  --hidden-import sensei_updater.ui.pages.cycle_page `
  --hidden-import sensei_updater.ui.pages.schedule_page `
  --hidden-import sensei_updater.ui.pages.reports_page `
  --hidden-import sensei_updater.ui.pages.settings_page `
  --add-data "$qss;sensei_updater/ui" `
  $entryPath

Write-Host "EXE ready: dist\$Name.exe"