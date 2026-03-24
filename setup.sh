#!/usr/bin/env bash
set -e

echo "Multi-Agent Orchestrator — Setup"
echo "================================="

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.12+ first."
    exit 1
fi

echo "Python: $(python3 --version)"

# Install dependencies
echo "Installing dependencies..."
pip install --break-system-packages -q pytest pytest-asyncio pyyaml 2>/dev/null \
    || pip install -q pytest pytest-asyncio pyyaml

# Check agents
echo ""
echo "Agent availability:"
for agent in codex opencode gemini kilo; do
    if command -v "$agent" &>/dev/null; then
        echo "  [OK] $agent"
    else
        echo "  [--] $agent (not installed — tasks will use fallback routing)"
    fi
done

# Create runtime directories
mkdir -p logs memory output

# Run tests
echo ""
echo "Running tests..."
python3 -m pytest tests/ -q

echo ""
echo "Setup complete. Run with:"
echo "  python3 orchestrator/main.py \"Your task here\""
