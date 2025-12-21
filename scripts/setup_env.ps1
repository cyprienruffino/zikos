# Setup script for Zikos environment configuration (PowerShell)
# Usage: .\scripts\setup_env.ps1 [small|medium|large|cpu]

param(
    [Parameter(Position=0)]
    [ValidateSet("small", "medium", "large", "cpu", "s", "m", "l", "c")]
    [string]$Profile = "small"
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvFile = Join-Path $ProjectRoot ".env"

# Normalize profile name
if ($Profile -eq "s") { $Profile = "small" }
if ($Profile -eq "m") { $Profile = "medium" }
if ($Profile -eq "l") { $Profile = "large" }
if ($Profile -eq "c") { $Profile = "cpu" }

switch ($Profile) {
    "cpu" {
        Write-Host "Setting up for CPU-only (no GPU)" -ForegroundColor Green
        @"
# Zikos Configuration - CPU-Only Setup (no GPU)
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# LLM Configuration - Optimized for CPU-only
# Model: Qwen2.5-7B-Instruct (recommended for CPU)
# Download: python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models
LLM_MODEL_PATH=./models/Qwen2.5-7B-Instruct-Q4_K_M.gguf
LLM_BACKEND=auto
LLM_N_CTX=16384
LLM_N_GPU_LAYERS=0
LLM_TEMPERATURE=0.7
LLM_TOP_P=0.9

# Storage paths
AUDIO_STORAGE_PATH=audio_storage
MIDI_STORAGE_PATH=midi_storage
NOTATION_STORAGE_PATH=notation_storage

# MCP Server
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8001

# Debug
DEBUG_TOOL_CALLS=false
"@ | Out-File -FilePath $EnvFile -Encoding utf8
        $ModelCmd = "python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models"
    }
    "small" {
        Write-Host "Setting up for Small GPU (8GB VRAM) - RTX 3060Ti, RTX 3070, etc." -ForegroundColor Green
        @"
# Zikos Configuration - Small GPU Setup (RTX 3060Ti / 8GB VRAM)
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# LLM Configuration - Optimized for 8GB VRAM
# Model: Qwen2.5-7B-Instruct (recommended)
# Download: python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models
LLM_MODEL_PATH=./models/Qwen2.5-7B-Instruct-Q4_K_M.gguf
LLM_BACKEND=auto
LLM_N_CTX=32768
LLM_N_GPU_LAYERS=-1
LLM_TEMPERATURE=0.7
LLM_TOP_P=0.9

# Storage paths
AUDIO_STORAGE_PATH=audio_storage
MIDI_STORAGE_PATH=midi_storage
NOTATION_STORAGE_PATH=notation_storage

# MCP Server
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8001

# Debug
DEBUG_TOOL_CALLS=false
"@ | Out-File -FilePath $EnvFile -Encoding utf8
        $ModelCmd = "python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models"
    }
    "medium" {
        Write-Host "Setting up for Medium GPU (16-24GB VRAM) - RTX 3090, RTX 4090, etc." -ForegroundColor Green
        @"
# Zikos Configuration - Medium GPU Setup (16-24GB VRAM)
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# LLM Configuration - Optimized for 16-24GB VRAM
# Model: Qwen2.5-14B-Instruct or Llama 3.3 70B
# Download: python scripts/download_model.py qwen2.5-14b-instruct-q4 -o ./models
LLM_MODEL_PATH=./models/Qwen2.5-14B-Instruct-Q4_K_M.gguf
LLM_BACKEND=auto
LLM_N_CTX=32768
LLM_N_GPU_LAYERS=-1
LLM_TEMPERATURE=0.7
LLM_TOP_P=0.9

# Storage paths
AUDIO_STORAGE_PATH=audio_storage
MIDI_STORAGE_PATH=midi_storage
NOTATION_STORAGE_PATH=notation_storage

# MCP Server
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8001

# Debug
DEBUG_TOOL_CALLS=false
"@ | Out-File -FilePath $EnvFile -Encoding utf8
        $ModelCmd = "python scripts/download_model.py qwen2.5-14b-instruct-q4 -o ./models"
    }
    "large" {
        Write-Host "Setting up for Large GPU (80GB+ VRAM) - H100, A100, etc." -ForegroundColor Green
        @"
# Zikos Configuration - Large GPU Setup (H100 / 80GB VRAM)
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# LLM Configuration - Optimized for 80GB VRAM
# Model: Qwen3-32B-Instruct (recommended)
# Download: python scripts/download_model.py qwen3-32b-instruct -o ./models
LLM_MODEL_PATH=./models/Qwen_Qwen3-32B-Instruct
LLM_BACKEND=transformers
LLM_N_CTX=131072
LLM_N_GPU_LAYERS=-1
LLM_TEMPERATURE=0.7
LLM_TOP_P=0.9

# Storage paths
AUDIO_STORAGE_PATH=audio_storage
MIDI_STORAGE_PATH=midi_storage
NOTATION_STORAGE_PATH=notation_storage

# MCP Server
MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8001

# Debug
DEBUG_TOOL_CALLS=false
"@ | Out-File -FilePath $EnvFile -Encoding utf8
        $ModelCmd = "python scripts/download_model.py qwen3-32b-instruct -o ./models"
    }
}

Write-Host ""
Write-Host "✓ Created .env file for $Profile profile" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Download a model:"
if ($Profile -eq "cpu" -or $Profile -eq "small") {
    Write-Host "   python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models" -ForegroundColor Yellow
} elseif ($Profile -eq "medium") {
    Write-Host "   python scripts/download_model.py qwen2.5-14b-instruct-q4 -o ./models" -ForegroundColor Yellow
} elseif ($Profile -eq "large") {
    Write-Host "   python scripts/download_model.py qwen3-32b-instruct -o ./models" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "2. Update LLM_MODEL_PATH in .env if needed"
Write-Host ""
Write-Host "3. Run the application:"
Write-Host "   python run.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "See CONFIGURATION.md for more details."
