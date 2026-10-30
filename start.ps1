# =============================================================================
# Agentic Test Data Simulator — Startup & Installer Script (PowerShell)
# =============================================================================
# This script sets up the Python virtual environment, installs backend dependencies,
# sets up .env, installs frontend npm packages, and launches both servers in separate windows.
# =============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "backend"
$FrontendDir = Join-Path $ScriptDir "frontend"
$VenvDir = Join-Path $BackendDir "venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$StopScript = Join-Path $ScriptDir "stop.ps1"

function Get-ListeningProcessIds {
    param([int]$Port)

    $processIds = @()
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        if ($connections) {
            $processIds += $connections | Select-Object -ExpandProperty OwningProcess
        }
    } catch {
        $netstatOutput = netstat -ano -p tcp 2>$null
        foreach ($line in $netstatOutput) {
            if ($line -match ":$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
                $processIds += [int]$Matches[1]
            }
        }
    }

    return @($processIds | Where-Object { $_ -gt 0 } | Select-Object -Unique)
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    Agentic LLM Test Data Simulator - Setup & Startup     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check Prerequisites ───────────────────────────────────────────────────
Write-Host "[1/5] Checking prerequisites..." -ForegroundColor Yellow

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}
$pythonVersion = & python --version 2>&1
Write-Host "  Found: $pythonVersion" -ForegroundColor Green

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if (-not $nodeCmd -or -not $npmCmd) {
    Write-Host "ERROR: Node.js / npm is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Please install Node.js 18+ from https://nodejs.org/" -ForegroundColor Red
    exit 1
}
$nodeVersion = & node --version 2>&1
$npmVersion = & npm --version 2>&1
Write-Host "  Found: Node $nodeVersion, npm $npmVersion" -ForegroundColor Green

# ── 2. Check and clear application ports ─────────────────────────────────────
Write-Host "`nChecking application ports..." -ForegroundColor Yellow
$busyPorts = @()
foreach ($port in @(8000, 3000)) {
    $portProcessIds = @(Get-ListeningProcessIds -Port $port)
    if ($portProcessIds.Count -gt 0) {
        Write-Host "  Port $port is in use by PID(s): $($portProcessIds -join ', ')." -ForegroundColor Yellow
        $busyPorts += $port
    } else {
        Write-Host "  Port $port is available." -ForegroundColor Green
    }
}

if ($busyPorts.Count -gt 0) {
    if (-not (Test-Path $StopScript)) {
        Write-Host "ERROR: Cannot clear occupied ports because stop.ps1 was not found." -ForegroundColor Red
        exit 1
    }

    Write-Host "  Running stop.ps1 to clear occupied application ports..." -ForegroundColor Yellow
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StopScript
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: stop.ps1 failed with exit code $LASTEXITCODE." -ForegroundColor Red
        exit 1
    }

    $portsStillBusy = @()
    foreach ($port in @(8000, 3000)) {
        if (@(Get-ListeningProcessIds -Port $port).Count -gt 0) {
            $portsStillBusy += $port
        }
    }
    if ($portsStillBusy.Count -gt 0) {
        Write-Host "ERROR: Port(s) $($portsStillBusy -join ', ') remain occupied; servers were not started." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Application ports are available." -ForegroundColor Green
}

# ── 3. Backend Environment & Configuration ──────────────────────────────────
Write-Host "`n[3/6] Configuring backend environment..." -ForegroundColor Yellow

$envFile = Join-Path $BackendDir ".env"
$envExample = Join-Path $BackendDir ".env.example"

if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item -Path $envExample -Destination $envFile
        Write-Host "  Created backend\.env from .env.example" -ForegroundColor Green
        Write-Host "  NOTE: Default provider is 'groq'. Edit backend\.env to set your API keys." -ForegroundColor Cyan
    } else {
        Write-Host "  WARNING: .env.example not found." -ForegroundColor Yellow
    }
} else {
    Write-Host "  backend\.env already exists." -ForegroundColor Green
}

# ── 4. Backend Virtual Environment & Dependencies ───────────────────────────
Write-Host "`n[4/6] Setting up Python virtual environment & dependencies..." -ForegroundColor Yellow

if (-not (Test-Path $VenvPython)) {
    Write-Host "  Creating virtual environment in backend\venv..." -ForegroundColor Gray
    & python -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
    Write-Host "  Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "  Existing virtual environment found in backend\venv." -ForegroundColor Green
}

$reqFile = Join-Path $BackendDir "requirements.txt"
if (Test-Path $reqFile) {
    Write-Host "  Updating pip, setuptools, and wheel in virtual environment..." -ForegroundColor Gray
    & $VenvPython -m pip install --upgrade pip setuptools wheel --quiet

    Write-Host "  Installing backend dependencies (preferring precompiled binary wheels)..." -ForegroundColor Gray
    & $VenvPython -m pip install --prefer-binary -r $reqFile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install Python dependencies." -ForegroundColor Red
        Write-Host "Hint: Ensure you have an active internet connection and pip is up to date." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  Backend dependencies are up to date." -ForegroundColor Green
}

# ── 5. Frontend Dependencies ─────────────────────────────────────────────────
Write-Host "`n[5/6] Setting up frontend dependencies..." -ForegroundColor Yellow
$frontendNodeModules = Join-Path $FrontendDir "node_modules"

if (-not (Test-Path $frontendNodeModules)) {
    Write-Host "  Installing frontend packages (npm install)... This may take a moment." -ForegroundColor Gray
    Push-Location $FrontendDir
    try {
        & npm install
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: npm install failed." -ForegroundColor Red
            exit 1
        }
    } finally {
        Pop-Location
    }
    Write-Host "  Frontend dependencies installed." -ForegroundColor Green
} else {
    Write-Host "  Frontend node_modules already installed." -ForegroundColor Green
}

# ── 6. Launch Servers ────────────────────────────────────────────────────────
Write-Host "`n[6/6] Launching Backend & Frontend servers..." -ForegroundColor Yellow

# Launch Backend in new window with explicit PYTHONPATH and venv python
$backendCmd = "`$Host.UI.RawUI.WindowTitle = 'Agentic TDM - Backend (Port 8000)'; Set-Location '$BackendDir'; `$env:PYTHONPATH = '$BackendDir'; & '$VenvPython' -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $backendCmd
Write-Host "  Backend started at: http://localhost:8000 (Docs: http://localhost:8000/docs)" -ForegroundColor Green

# Launch Frontend in new window
$frontendCmd = "`$Host.UI.RawUI.WindowTitle = 'Agentic TDM - Frontend (Port 3000)'; Set-Location '$FrontendDir'; npm run dev"
Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $frontendCmd
Write-Host "  Frontend started at: http://localhost:3000" -ForegroundColor Green

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Both servers are now running in separate terminal windows! " -ForegroundColor Cyan
Write-Host " Open your browser at: http://localhost:3000              " -ForegroundColor Green
Write-Host " To shut down both servers, run .\stop.ps1 or stop.bat    " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

Start-Sleep -Seconds 3
Start-Process "http://localhost:3000" -ErrorAction SilentlyContinue
