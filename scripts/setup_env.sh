#!/bin/bash
# Setup script for Zikos environment configuration
# Usage: ./scripts/setup_env.sh [small|medium|large|cpu]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Determine hardware profile
PROFILE="${1:-small}"

case "$PROFILE" in
    cpu|c)
        echo "Setting up for CPU-only (no GPU)"
        cat > "$ENV_FILE" << 'EOF'
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
EOF
        ;;
    small|s)
        echo "Setting up for Small GPU (8GB VRAM) - RTX 3060Ti, RTX 3070, etc."
        cat > "$ENV_FILE" << 'EOF'
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
EOF
        ;;
    medium|m)
        echo "Setting up for Medium GPU (16-24GB VRAM) - RTX 3090, RTX 4090, etc."
        cat > "$ENV_FILE" << 'EOF'
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
EOF
        ;;
    large|l)
        echo "Setting up for Large GPU (80GB+ VRAM) - H100, A100, etc."
        cat > "$ENV_FILE" << 'EOF'
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
EOF
        ;;
    *)
        echo "Usage: $0 [small|medium|large|cpu]"
        echo ""
        echo "Profiles:"
        echo "  small  - RTX 3060Ti / 8GB VRAM"
        echo "  medium - RTX 3090/4090 / 16-24GB VRAM"
        echo "  large  - H100 / 80GB+ VRAM"
        echo "  cpu    - CPU-only (no GPU)"
        exit 1
        ;;
esac

echo ""
echo "✓ Created .env file for $PROFILE profile"
echo ""
echo "Next steps:"
echo "1. Download a model:"
case "$PROFILE" in
    small|cpu)
        echo "   python scripts/download_model.py qwen2.5-7b-instruct-q4 -o ./models"
        ;;
    medium)
        echo "   python scripts/download_model.py qwen2.5-14b-instruct-q4 -o ./models"
        ;;
    large)
        echo "   python scripts/download_model.py qwen3-32b-instruct -o ./models"
        ;;
esac
echo ""
echo "2. Update LLM_MODEL_PATH in .env if needed"
echo ""
echo "3. Run the application:"
echo "   python run.py"
echo ""
echo "See CONFIGURATION.md for more details."
