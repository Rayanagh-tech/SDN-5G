# ============================================================================
# 5G Network Slicing - PowerShell Quick Start Script (Windows)
# ============================================================================
# This script automates the setup and execution on Windows with WSL2.
#
# Usage:
#   .\run_experiment.ps1
# ============================================================================

param(
    [int]$Duration = 60,
    [switch]$SkipELK = $false
)

Write-Host "============================================" -ForegroundColor Blue
Write-Host "  5G Network Slicing Experiment (Windows)" -ForegroundColor Blue
Write-Host "============================================" -ForegroundColor Blue
Write-Host ""

# Function to check if Docker is running
function Test-DockerRunning {
    try {
        docker info 2>&1 | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Function to wait for service
function Wait-ForService {
    param(
        [string]$Url,
        [int]$MaxAttempts = 30,
        [int]$DelaySeconds = 5
    )
    
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {
            Write-Host "  Waiting... ($i/$MaxAttempts)" -ForegroundColor Yellow
        }
        Start-Sleep -Seconds $DelaySeconds
    }
    return $false
}

# Step 1: Check prerequisites
Write-Host "Step 1: Checking prerequisites..." -ForegroundColor Blue

if (-not (Test-DockerRunning)) {
    Write-Host "Error: Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}
Write-Host "  Docker: OK" -ForegroundColor Green

# Check if WSL is available
$wslInstalled = wsl --list 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: WSL may not be installed. Mininet requires Linux." -ForegroundColor Yellow
}
Write-Host ""

# Step 2: Create directories
Write-Host "Step 2: Creating required directories..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path "monitoring\metrics" | Out-Null
New-Item -ItemType Directory -Force -Path "monitoring\logs" | Out-Null
Write-Host "  Directories created" -ForegroundColor Green
Write-Host ""

# Step 3: Start ELK Stack
if (-not $SkipELK) {
    Write-Host "Step 3: Starting ELK stack..." -ForegroundColor Blue
    
    $elkStatus = docker-compose ps 2>&1
    if ($elkStatus -match "Up") {
        Write-Host "  ELK stack already running" -ForegroundColor Yellow
    } else {
        docker-compose up -d
        
        Write-Host "  Waiting for Elasticsearch to be ready..." -ForegroundColor Yellow
        if (Wait-ForService -Url "http://localhost:9200" -MaxAttempts 30 -DelaySeconds 5) {
            Write-Host "  Elasticsearch ready" -ForegroundColor Green
        } else {
            Write-Host "  Warning: Elasticsearch may not be ready" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "Step 3: Skipping ELK stack (--SkipELK specified)" -ForegroundColor Yellow
}
Write-Host ""

# Step 4: Instructions for running in WSL
Write-Host "Step 4: Running the experiment" -ForegroundColor Blue
Write-Host ""
Write-Host "The SDN components require Linux. Run the following in WSL2:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  # Terminal 1: Start Ryu Controller" -ForegroundColor Cyan
Write-Host "  cd /mnt/c/Users/HP/Desktop/SDN-5G"
Write-Host "  ryu-manager --ofp-tcp-listen-port 6653 --wsapi-port 8080 controller.py"
Write-Host ""
Write-Host "  # Terminal 2: Start Mininet (requires sudo)" -ForegroundColor Cyan
Write-Host "  cd /mnt/c/Users/HP/Desktop/SDN-5G"
Write-Host "  sudo python3 topology.py"
Write-Host ""
Write-Host "  # In Mininet CLI, run:" -ForegroundColor Cyan
Write-Host "  server iperf3 -s -p 5001 -D"
Write-Host "  server iperf3 -s -p 5002 -D"
Write-Host "  server iperf3 -s -p 5003 -D"
Write-Host "  urllc_h1 iperf3 -c 10.0.0.100 -u -p 5001 -b 5M -t $Duration &"
Write-Host "  embb_h1 iperf3 -c 10.0.0.100 -u -p 5002 -b 50M -t $Duration &"
Write-Host "  mmtc_h1 iperf3 -c 10.0.0.100 -u -p 5003 -b 1M -t $Duration &"
Write-Host ""
Write-Host "  # Terminal 3: Collect metrics" -ForegroundColor Cyan
Write-Host "  cd /mnt/c/Users/HP/Desktop/SDN-5G"
Write-Host "  python3 monitoring/metrics_collector.py --duration 120"
Write-Host ""

# Step 5: Open Kibana
Write-Host "Step 5: Opening Kibana dashboard..." -ForegroundColor Blue
Start-Process "http://localhost:5601"
Write-Host ""

Write-Host "============================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access points:" -ForegroundColor Cyan
Write-Host "  - Kibana:        http://localhost:5601"
Write-Host "  - Elasticsearch: http://localhost:9200"
Write-Host "  - Logstash:      http://localhost:5044"
Write-Host ""
Write-Host "To stop ELK stack:" -ForegroundColor Yellow
Write-Host "  docker-compose down"
Write-Host ""
