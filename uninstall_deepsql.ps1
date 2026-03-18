param(
    [string]$Model = "deepseek-coder-v2:16b",
    [switch]$PurgeOllamaHome,
    [switch]$UninstallPython,
    [switch]$UninstallOllama,
    [switch]$Force
)

$ErrorActionPreference = "Continue"
$StateFilePath = Join-Path $PSScriptRoot ".deepsql-install-state.json"

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Remove-PathIfExists($path) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force
        Write-Host "Eliminado: $path" -ForegroundColor Yellow
    }
}

function Test-CommandAvailable($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Confirm-Action($message) {
    if ($Force) {
        return $true
    }

    $answer = Read-Host "$message [s/N]"
    return $answer -match '^(s|si|y|yes)$'
}

$state = $null
if (Test-Path $StateFilePath) {
    try {
        $state = Get-Content $StateFilePath -Raw | ConvertFrom-Json
    }
    catch {
        Write-Host "No se pudo leer estado de instalacion. Se usaran valores por defecto." -ForegroundColor Yellow
    }
}

$modelToRemove = if ($state -and $state.model) { [string]$state.model } else { $Model }

Write-Step "Eliminando artefactos locales del proyecto"
Remove-PathIfExists (Join-Path $PSScriptRoot ".venv")
Remove-PathIfExists (Join-Path $PSScriptRoot "__pycache__")
Remove-PathIfExists (Join-Path $PSScriptRoot ".pytest_cache")

if ($state -and $state.connections_created -and (Test-Path (Join-Path $PSScriptRoot "connections.toml"))) {
    Remove-PathIfExists (Join-Path $PSScriptRoot "connections.toml")
}

if ((Test-CommandAvailable "ollama") -and $modelToRemove) {
    Write-Step "Eliminando modelo de Ollama: $modelToRemove"
    ollama rm $modelToRemove | Out-Host
}

$purgeOllamaHomeEffective = $PurgeOllamaHome
if (-not $purgeOllamaHomeEffective -and $state -and ($state.ollama_home_preexisting -eq $false)) {
    $purgeOllamaHomeEffective = $true
}

if ($purgeOllamaHomeEffective) {
    $ollamaHome = Join-Path $env:USERPROFILE ".ollama"
    if (Test-Path $ollamaHome) {
        if (Confirm-Action "Se eliminara por completo $ollamaHome") {
            Remove-PathIfExists $ollamaHome
        }
    }
}

$shouldUninstallOllama = $UninstallOllama
if (-not $shouldUninstallOllama -and $state -and ($state.ollama_was_present -eq $false)) {
    $shouldUninstallOllama = $true
}

if ($shouldUninstallOllama -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Step "Desinstalando Ollama"
    winget uninstall --id Ollama.Ollama -e --source winget --accept-source-agreements | Out-Host
}

$shouldUninstallPython = $UninstallPython
if (-not $shouldUninstallPython -and $state -and ($state.python_was_present -eq $false)) {
    $shouldUninstallPython = $true
}

if ($shouldUninstallPython -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Step "Desinstalando Python 3.11"
    winget uninstall --id Python.Python.3.11 -e --source winget --accept-source-agreements | Out-Host
}

Remove-PathIfExists $StateFilePath

Write-Host "`nDesinstalacion finalizada." -ForegroundColor Green
