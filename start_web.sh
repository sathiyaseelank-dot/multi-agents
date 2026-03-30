#!/usr/bin/env bash
# Start the Multi-Agent Orchestrator Web Interface

set -e

echo "==================================="
echo "  Multi-Agent Orchestrator Web UI"
echo "==================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if Flask API dependencies are installed
if ! python3 -c "import flask_cors" 2>/dev/null; then
    echo "Installing Flask API dependencies..."
    pip install -q -r flask_api/requirements.txt
fi

# Check if Node.js is available for frontend
if command -v npm &>/dev/null; then
    echo "Node.js found: $(node --version)"
    
    # Install frontend dependencies if needed
    if [ ! -d "frontend/node_modules" ]; then
        echo "Installing frontend dependencies..."
        cd frontend
        npm install
        cd ..
    fi
fi

echo ""
echo "Starting Flask API server..."
echo ""
echo "🌐 API will be available at: http://localhost:5000"
echo "📊 Frontend will be available at: http://localhost:5173 (after running npm run dev)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start Flask API
cd flask_api
python3 app.py
