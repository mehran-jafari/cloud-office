# Cloud Office Desk - Windows installer
# Usage (PowerShell):
#   powershell -NoProfile -ExecutionPolicy Bypass -Command "iwr -useb '__APP_URL__/api/desk/agent/windows/?app=__APP_URL__' | iex"
$ErrorActionPreference = 'Stop'
$AppUrl   = '__APP_URL__'
$AppName  = 'Cloud Office Desk'
$InstallDir = Join-Path $env:LOCALAPPDATA 'CloudOfficeDesk'
$Desktop  = [Environment]::GetFolderPath('Desktop')
$StartMenu = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'

function Remove-Desk {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $InstallDir
    Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $Desktop "$AppName.lnk")
    Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $StartMenu "$AppName.lnk")
}

try {
    if ($env:CLOUD_OFFICE_UNINSTALL -eq '1') {
        Remove-Desk
        Write-Host "Removed $AppName." -ForegroundColor Green
        return
    }

    Write-Host "=== Installing $AppName (Windows) ===" -ForegroundColor Cyan
    Write-Host "Server: $AppUrl"
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

    # Launcher: standalone app window in Edge/Chrome, else default browser.
    $launcher = @"
@echo off
set "URL=$AppUrl/remote-support?agent=1"
set "BROWSER="
for %%P in (
  "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
  "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
  "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
  "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do if not defined BROWSER if exist %%P set "BROWSER=%%~P"
if defined BROWSER (
  start "" "%BROWSER%" --app="%URL%"
) else (
  start "" "%URL%"
)
"@
    $launcherPath = Join-Path $InstallDir 'Start-DeskAgent.cmd'
    [System.IO.File]::WriteAllText($launcherPath, ($launcher -replace "`r?`n", "`r`n"), (New-Object System.Text.ASCIIEncoding))

    $shell = New-Object -ComObject WScript.Shell
    foreach ($dir in @($Desktop, $StartMenu)) {
        if (-not (Test-Path $dir)) { continue }
        $lnk = $shell.CreateShortcut((Join-Path $dir "$AppName.lnk"))
        $lnk.TargetPath = $launcherPath
        $lnk.WorkingDirectory = $InstallDir
        $lnk.WindowStyle = 7
        $lnk.Description = 'Cloud Office secure remote connection'
        $lnk.Save()
    }

    Set-Content -Path (Join-Path $InstallDir 'installed.flag') -Value (Get-Date -Format o)
    Set-Content -Path (Join-Path $InstallDir 'server.url') -Value $AppUrl

    Write-Host "Installed: $InstallDir" -ForegroundColor Green
    Write-Host "A shortcut was created on the Desktop and in the Start Menu." -ForegroundColor Green
    Start-Process -FilePath $launcherPath -WindowStyle Hidden
}
catch {
    Write-Host "Install failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please send this message to your administrator."
    if ($Host.Name -eq 'ConsoleHost' -and -not $env:CLOUD_OFFICE_NOPAUSE) { Read-Host 'Press Enter to close' | Out-Null }
}
