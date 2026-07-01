param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $Root "work\runtime"
$PidFile = Join-Path $RuntimeDir "targetsafe_pids.json"
New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Test-Url($Url) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
    return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
  } catch {
    return $false
  }
}

function Wait-Url($Url, $Label) {
  for ($i = 0; $i -lt 30; $i++) {
    if (Test-Url $Url) { return $true }
    Start-Sleep -Milliseconds 500
  }
  throw "$Label did not become ready at $Url"
}

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}

$BackendUrl = "http://127.0.0.1:$BackendPort/api/health"
$FrontendUrl = "http://127.0.0.1:$FrontendPort/"
$backendProcess = $null
$frontendProcess = $null

if (-not (Test-Url $BackendUrl)) {
  $backendProcess = Start-Process -FilePath $Python -ArgumentList @("-m", "uvicorn", "targetsafe.api:app", "--host", "127.0.0.1", "--port", "$BackendPort") -WorkingDirectory $Root -WindowStyle Hidden -PassThru
  Wait-Url $BackendUrl "Target-SAFE backend" | Out-Null
}

if (-not (Test-Url $FrontendUrl)) {
  $Npm = "npm"
  if ($IsWindows -or $env:OS -eq "Windows_NT") {
    $Npm = "npm.cmd"
  }
  $frontendProcess = Start-Process -FilePath $Npm -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$FrontendPort") -WorkingDirectory (Join-Path $Root "frontend") -WindowStyle Hidden -PassThru
  Wait-Url $FrontendUrl "Target-SAFE frontend" | Out-Null
}

$payload = [ordered]@{
  backend_pid = if ($backendProcess) { $backendProcess.Id } else { $null }
  frontend_pid = if ($frontendProcess) { $frontendProcess.Id } else { $null }
  backend_url = "http://127.0.0.1:$BackendPort"
  frontend_url = $FrontendUrl
  started_at = (Get-Date).ToString("o")
}
$payload | ConvertTo-Json | Set-Content -Encoding UTF8 $PidFile

Write-Host "Target-SAFE is ready."
Write-Host "Frontend: $FrontendUrl"
Write-Host "Backend:  http://127.0.0.1:$BackendPort"
Write-Host "PID file: $PidFile"
