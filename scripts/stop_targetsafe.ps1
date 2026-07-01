$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root "work\runtime\targetsafe_pids.json"

if (-not (Test-Path $PidFile)) {
  Write-Host "No Target-SAFE PID file found."
  exit 0
}

$payload = Get-Content $PidFile | ConvertFrom-Json
$targetPids = @($payload.backend_pid, $payload.frontend_pid) | Where-Object { $_ -ne $null }
foreach ($targetPid in $targetPids) {
  try {
    $process = Get-Process -Id $targetPid -ErrorAction Stop
    Stop-Process -Id $process.Id -Force
    Write-Host "Stopped Target-SAFE process $targetPid"
  } catch {
    Write-Host "Process $targetPid is not running."
  }
}

Remove-Item -LiteralPath $PidFile -Force
Write-Host "Target-SAFE runtime state cleared."
