# =============================================================================
# Agentic Test Data Simulator — Server Terminator Script (PowerShell)
# =============================================================================
# Gracefully stops both the FastAPI backend (Port 8000) and Next.js frontend (Port 3000).
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    Agentic LLM Test Data Simulator - Stopping Servers    " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

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

$stopFailed = $false

function Stop-PortProcess {
    param(
        [int]$Port,
        [string]$ServiceName
    )

    Write-Host "Checking for $ServiceName running on port $Port..." -ForegroundColor Yellow
    $uniquePids = @(Get-ListeningProcessIds -Port $Port | Where-Object { $_ -ne $PID })

    if ($uniquePids.Count -gt 0) {
        foreach ($processId in $uniquePids) {
            try {
                $proc = Get-Process -Id $processId -ErrorAction Stop
                Write-Host "  Terminating PID ${processId} ($($proc.ProcessName)) on port $Port..." -ForegroundColor Gray
                Stop-Process -Id $processId -Force -ErrorAction Stop
                Wait-Process -Id $processId -Timeout 5 -ErrorAction SilentlyContinue
            } catch {
                $stillRunning = Get-Process -Id $processId -ErrorAction SilentlyContinue
                if ($stillRunning) {
                    Write-Host "  ERROR: Could not stop PID ${processId} on port ${Port}: $($_.Exception.Message)" -ForegroundColor Red
                    $script:stopFailed = $true
                }
            }
        }

        $remainingPids = @(Get-ListeningProcessIds -Port $Port)
        if ($remainingPids.Count -gt 0) {
            Write-Host "  ERROR: Port $Port is still occupied by PID(s): $($remainingPids -join ', ')." -ForegroundColor Red
            $script:stopFailed = $true
        } else {
            Write-Host "  $ServiceName stopped; port $Port is available." -ForegroundColor Green
        }
    } else {
        Write-Host "  No active process found listening on port $Port." -ForegroundColor DarkGray
    }
}

# Stop Backend on Port 8000
Stop-PortProcess -Port 8000 -ServiceName "FastAPI Backend"

# Stop Frontend on Port 3000
Stop-PortProcess -Port 3000 -ServiceName "Next.js Frontend"

# Close the launcher terminals when they are still open.
$windowTitles = @("Agentic TDM - Backend*", "Agentic TDM - Frontend*")
foreach ($title in $windowTitles) {
    $terminals = @(Get-Process -Name powershell -ErrorAction SilentlyContinue |
        Where-Object { $_.Id -ne $PID -and $_.MainWindowTitle -like $title })
    foreach ($terminal in $terminals) {
        try {
            Write-Host "Closing terminal window: $($terminal.MainWindowTitle)" -ForegroundColor Gray
            if (-not $terminal.CloseMainWindow()) {
                Stop-Process -Id $terminal.Id -Force -ErrorAction Stop
            } else {
                $terminal.WaitForExit(3000)
                if (-not $terminal.HasExited) {
                    Stop-Process -Id $terminal.Id -Force -ErrorAction Stop
                }
            }
        } catch {
            Write-Host "  ERROR: Could not close terminal PID $($terminal.Id): $($_.Exception.Message)" -ForegroundColor Red
            $script:stopFailed = $true
        }
    }
}

Write-Host ""
if ($stopFailed) {
    Write-Host "==========================================================" -ForegroundColor Red
    Write-Host " One or more servers could not be stopped.                " -ForegroundColor Red
    Write-Host "==========================================================" -ForegroundColor Red
    exit 1
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " All servers have been stopped.                            " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
exit 0
