$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
  $Python = "python"
}

function Test-Url($Url) {
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
    return "$($response.StatusCode) OK"
  } catch {
    return "unreachable: $($_.Exception.Message)"
  }
}

Write-Host "Target-SAFE environment check"
Write-Host "Root: $Root"
Write-Host ""
Write-Host "Python:"
& $Python -c "import sys; print(sys.executable); print(sys.version)"
Write-Host ""
Write-Host "GPU diagnostics:"
& $Python -c "import json; from targetsafe.embeddings import gpu_diagnostics; print(json.dumps(gpu_diagnostics(), indent=2))"
Write-Host ""
Write-Host "Node / npm:"
node --version
npm --version
Write-Host ""
Write-Host "Backend health:  $(Test-Url 'http://127.0.0.1:8000/api/health')"
Write-Host "Frontend health: $(Test-Url 'http://127.0.0.1:5173/')"
Write-Host ""
Write-Host "LLM environment keys are reported as configured/not configured by /api/runtime-status; raw secrets are not printed here."
