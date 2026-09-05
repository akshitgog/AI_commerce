param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("backend", "frontend")]
    [string]$Service
)

$repositoryRoot = Split-Path -Parent $PSScriptRoot

if ($Service -eq "backend") {
    Set-Location $repositoryRoot
    uv run uvicorn ai_commerce_gateway.api.app:app --host 127.0.0.1 --port 8000 --reload
    exit $LASTEXITCODE
}

Set-Location (Join-Path $repositoryRoot "frontend")
npm run dev
