param(
    [string]$Model = "deepseek-coder-v2:16b",
    [switch]$LaunchApp,
    [switch]$SkipPythonInstall,
    [switch]$SkipOllamaInstall,
    [switch]$SkipModelPull
)

$ErrorActionPreference = "Stop"
$StateFilePath = Join-Path $PSScriptRoot ".deepsql-install-state.json"

$InstallState = [ordered]@{
    model = $Model
    python_was_present = $false
    ollama_was_present = $false
    venv_created = $false
    connections_created = $false
    model_pulled = $false
    ollama_home_preexisting = $false
}

function Write-Step($msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

function Ensure-Command($name, $hint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "No se encontro '$name'. $hint"
    }
}

function Save-InstallState {
    $InstallState | ConvertTo-Json -Depth 4 | Set-Content -Path $StateFilePath -Encoding UTF8
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $false)][string[]]$Arguments = @()
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    return $true
}

function Test-Winget {
    return [bool](Get-Command winget -ErrorAction SilentlyContinue)
}

function Test-CommandAvailable($name) {
    return [bool](Get-Command $name -ErrorAction SilentlyContinue)
}

function Test-OllamaModelExists($modelName) {
    if (-not (Test-CommandAvailable "ollama")) {
        return $false
    }

    try {
        $out = ollama list
    }
    catch {
        return $false
    }

    return [bool]($out | Select-String -Pattern ("^" + [Regex]::Escape($modelName) + "\s"))
}

function Get-PyInstalledVersions {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        return @()
    }

    $out = & py --list 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $out) {
        return @()
    }

    $text = ($out -join "`n")
    $matches = [Regex]::Matches($text, "-V:([0-9]+\.[0-9]+)")
    $versions = @()
    foreach ($m in $matches) {
        $v = $m.Groups[1].Value
        if ($v -and -not ($versions -contains $v)) {
            $versions += $v
        }
    }

    if ($versions.Count -eq 0) {
        # Fallback for py output styles like: -3.11-64
        $legacyMatches = [Regex]::Matches($text, "-([0-9]+\.[0-9]+)(?:-[0-9]+)?")
        foreach ($m in $legacyMatches) {
            $v = $m.Groups[1].Value
            if ($v -and -not ($versions -contains $v)) {
                $versions += $v
            }
        }
    }

    return $versions
}

function Install-WithWinget($id, $name) {
    if (-not (Test-Winget)) {
        throw "Winget no esta disponible. Instala '$name' manualmente."
    }

    Write-Step "Instalando $name (winget: $id)"
    winget install --id $id -e --source winget --accept-source-agreements --accept-package-agreements
}

function Resolve-PythonExe {
    $venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        return $venvPython
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        return "py"
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }

    return $null
}

function Ensure-Python {
    $pythonCmd = Resolve-PythonExe
    if ($pythonCmd) {
        return $false
    }

    if ($SkipPythonInstall) {
        throw "Python no esta instalado y se indico -SkipPythonInstall."
    }

    Install-WithWinget "Python.Python.3.11" "Python 3.11"
    return $true
}

function Ensure-Ollama {
    if (Get-Command ollama -ErrorAction SilentlyContinue) {
        return $false
    }

    if ($SkipOllamaInstall) {
        throw "Ollama no esta instalado y se indico -SkipOllamaInstall."
    }

    Install-WithWinget "Ollama.Ollama" "Ollama"
    return $true
}

function Invoke-Python($argsList) {
    $pythonExe = Resolve-PythonExe
    if (-not $pythonExe) {
        throw "No se pudo resolver Python despues de la instalacion. Cierra y vuelve a abrir la terminal."
    }

    if ($pythonExe -eq "py") {
        & py @argsList
        return
    }

    & $pythonExe @argsList
}

Write-Step "Validando prerequisitos base"
$InstallState.python_was_present = ((Test-CommandAvailable "python") -or (Test-CommandAvailable "py"))
$InstallState.ollama_was_present = (Test-CommandAvailable "ollama")
$InstallState.ollama_home_preexisting = Test-Path (Join-Path $env:USERPROFILE ".ollama")

$pythonInstalledNow = Ensure-Python
$ollamaInstalledNow = Ensure-Ollama

if ($pythonInstalledNow) {
    $InstallState.python_was_present = $false
}
if ($ollamaInstalledNow) {
    $InstallState.ollama_was_present = $false
}

$venvPath = Join-Path $PSScriptRoot ".venv"
$venvPython = Join-Path $venvPath "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Step "Creando entorno virtual (.venv)"
    $venvCreated = $false

    if (Get-Command py -ErrorAction SilentlyContinue) {
        $availablePyVersions = Get-PyInstalledVersions
        $targetVersion = $null

        if ($availablePyVersions -contains "3.11") {
            $targetVersion = "3.11"
        }
        elseif ($availablePyVersions.Count -gt 0) {
            # Choose the first version reported by py launcher.
            $targetVersion = $availablePyVersions[0]
        }

        if ($targetVersion) {
            $venvCreated = Invoke-CheckedCommand -FilePath "py" -Arguments @("-$targetVersion", "-m", "venv", $venvPath)
        }

        if (-not $venvCreated -and $availablePyVersions.Count -gt 0) {
            $venvCreated = Invoke-CheckedCommand -FilePath "py" -Arguments @("-m", "venv", $venvPath)
        }
    }

    if ((-not $venvCreated) -and (Get-Command python -ErrorAction SilentlyContinue)) {
        $venvCreated = Invoke-CheckedCommand -FilePath "python" -Arguments @("-m", "venv", $venvPath)
    }

    if (-not $venvCreated -or -not (Test-Path $venvPython)) {
        throw "No se pudo crear el entorno virtual '.venv'. Instala Python 3.11+ y vuelve a ejecutar el setup. Sugerencia: py install 3.11"
    }

    $InstallState.venv_created = $true
}

Write-Step "Actualizando pip e instalando dependencias"
if (-not (Test-Path $venvPython)) {
    throw "No se encontro python del entorno virtual en '$venvPython'."
}

if (-not (Invoke-CheckedCommand -FilePath $venvPython -Arguments @("-m", "pip", "install", "--upgrade", "pip"))) {
    throw "Fallo actualizando pip dentro de .venv."
}

if (-not (Invoke-CheckedCommand -FilePath $venvPython -Arguments @("-m", "pip", "install", "streamlit", "pandas", "langchain", "langchain-community", "langchain-ollama", "streamlit-mic-recorder", "sqlalchemy", "psycopg2-binary"))) {
    throw "Fallo instalando dependencias Python dentro de .venv."
}

if (-not (Test-Path (Join-Path $PSScriptRoot "connections.toml")) -and (Test-Path (Join-Path $PSScriptRoot "connections.toml.example"))) {
    Write-Step "Creando connections.toml desde plantilla"
    Copy-Item (Join-Path $PSScriptRoot "connections.toml.example") (Join-Path $PSScriptRoot "connections.toml")
    $InstallState.connections_created = $true
}

if (-not $SkipModelPull) {
    Write-Step "Descargando modelo Ollama: $Model"
    $modelAlreadyExists = Test-OllamaModelExists $Model

    # Intenta iniciar el servicio si no estaba activo.
    try {
        ollama list | Out-Null
    }
    catch {
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden | Out-Null
        Start-Sleep -Seconds 2
    }

    if (-not (Invoke-CheckedCommand -FilePath "ollama" -Arguments @("pull", $Model))) {
        throw "Fallo descargando el modelo de Ollama: $Model"
    }

    if (-not $modelAlreadyExists) {
        $InstallState.model_pulled = $true
    }
}

Save-InstallState

if ($LaunchApp) {
    Write-Step "Lanzando app Streamlit"
    & $venvPython -m streamlit run (Join-Path $PSScriptRoot "ChatSQL-PROMPT.py")
}
else {
    Write-Host "`nInstalacion finalizada." -ForegroundColor Green
    Write-Host "Para lanzar la app:" -ForegroundColor Yellow
    Write-Host "  .\.venv\Scripts\python.exe -m streamlit run ChatSQL-PROMPT.py"
    Write-Host "Se registro estado de instalacion en: $StateFilePath"
}
