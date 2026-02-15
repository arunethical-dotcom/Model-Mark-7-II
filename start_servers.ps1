# JARVIIS llama.cpp Server Launcher
# Launches both Qwen (governance) and Mistral (reasoning) servers

$MODEL_DIR = "C:\Users\Arun\model\Cursor Int\local model"
$QWEN_MODEL = "Qwen2.5-1.5B-Instruct-Q4_K_M.gguf"
$MISTRAL_MODEL = "Mistral-7B-Instruct-v0.2-Q4_K_M.gguf"

Write-Host "================================" -ForegroundColor Cyan
Write-Host "JARVIIS llama.cpp Server Launcher" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if llama-server is available
if (-not (Get-Command llama-server -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: llama-server not found in PATH" -ForegroundColor Red
    Write-Host "Please ensure llama.cpp is installed and llama-server is in your PATH" -ForegroundColor Yellow
    exit 1
}

# Check if model files exist
if (-not (Test-Path (Join-Path $MODEL_DIR $QWEN_MODEL))) {
    Write-Host "ERROR: Qwen model not found at $MODEL_DIR\$QWEN_MODEL" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path (Join-Path $MODEL_DIR $MISTRAL_MODEL))) {
    Write-Host "ERROR: Mistral model not found at $MODEL_DIR\$MISTRAL_MODEL" -ForegroundColor Red
    exit 1
}

Write-Host "✓ llama-server found" -ForegroundColor Green
Write-Host "✓ Model files verified" -ForegroundColor Green
Write-Host ""

# Launch Mistral server (Reasoning - port 8080)
Write-Host "Starting Mistral 7B server (Reasoning) on port 8080..." -ForegroundColor Yellow
$mistralJob = Start-Job -ScriptBlock {
    param($modelDir, $model)
    Set-Location $modelDir
    llama-server `
        -m $model `
        --host 0.0.0.0 `
        --port 8080 `
        --threads 4 `
        --ctx-size 2048 `
        --n-predict 512
} -ArgumentList $MODEL_DIR, $MISTRAL_MODEL

Start-Sleep -Seconds 2

# Launch Qwen server (Governance - port 8081)
Write-Host "Starting Qwen 1.5B server (Governance) on port 8081..." -ForegroundColor Yellow
$qwenJob = Start-Job -ScriptBlock {
    param($modelDir, $model)
    Set-Location $modelDir
    llama-server `
        -m $model `
        --host 0.0.0.0 `
        --port 8081 `
        --threads 4 `
        --ctx-size 2048 `
        --n-predict 256
} -ArgumentList $MODEL_DIR, $QWEN_MODEL

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Servers Starting..." -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Mistral (Reasoning):  http://localhost:8080" -ForegroundColor Green
Write-Host "Qwen (Governance):    http://localhost:8081" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop both servers" -ForegroundColor Yellow
Write-Host ""

# Wait for user interrupt
try {
    while ($true) {
        Start-Sleep -Seconds 1
        
        # Check if jobs are still running
        if ($mistralJob.State -ne "Running") {
            Write-Host "WARNING: Mistral server stopped unexpectedly" -ForegroundColor Red
            Receive-Job -Job $mistralJob
        }
        if ($qwenJob.State -ne "Running") {
            Write-Host "WARNING: Qwen server stopped unexpectedly" -ForegroundColor Red
            Receive-Job -Job $qwenJob
        }
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping servers..." -ForegroundColor Yellow
    Stop-Job -Job $mistralJob, $qwenJob
    Remove-Job -Job $mistralJob, $qwenJob
    Write-Host "Servers stopped." -ForegroundColor Green
}
