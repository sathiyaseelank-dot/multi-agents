# Multi-Agent Orchestrator - Web Interface

Access the orchestrator through a web browser!

---

## 🚀 Quick Start

### Option 1: Start Web Interface (Recommended)

```bash
# Make script executable (first time only)
chmod +x start_web.sh

# Start the web interface
./start_web.sh
```

Then open your browser to:
- **Frontend UI**: http://localhost:5173
- **API Server**: http://localhost:5000

### Option 2: Start Components Separately

**Terminal 1 - Flask API:**
```bash
cd flask_api
python3 app.py
```

**Terminal 2 - Frontend (optional):**
```bash
cd frontend
npm install    # First time only
npm run dev
```

---

## 📡 API Endpoints

### Run a Task
```bash
POST http://localhost:5000/api/orchestrator/run
Content-Type: application/json

{
    "task": "Build a REST API with user authentication"
}
```

Response:
```json
{
    "session_id": "20260325-101850",
    "status": "started",
    "message": "Task queued for execution"
}
```

### Check Status
```bash
GET http://localhost:5000/api/orchestrator/status/{session_id}
```

### Get Results
```bash
GET http://localhost:5000/api/orchestrator/results/{session_id}
```

### List Sessions
```bash
GET http://localhost:5000/api/orchestrator/sessions?limit=10
```

### Health Check
```bash
GET http://localhost:5000/api/orchestrator/health
```

---

## 🖥️ Web UI Features

### New Task Tab
- Enter task description
- Example tasks to click and load
- Start execution with progress tracking

### Status Tab
- Real-time execution status
- Live event feed
- Session information

### History Tab
- List of all sessions
- Filter by status
- Quick access to results

### Results Tab
- Full execution results
- Build artifacts
- Validation and runtime results
- Meta-controller decisions

---

## 📊 Example Workflow

1. **Open UI**: Navigate to http://localhost:5173

2. **Enter Task**: 
   ```
   Build a Flask REST API with CRUD endpoints for a todo app
   ```

3. **Click "Run Task"**: Task starts executing

4. **Monitor Status**: Watch real-time progress in Status tab

5. **View Results**: Once complete, see:
   - Project directory location
   - Generated files
   - Validation results
   - Runtime execution logs
   - Evaluation score

---

## 🔧 Troubleshooting

### API Not Starting
```bash
# Check if port 5000 is in use
lsof -i :5000

# Kill existing process if needed
kill -9 <PID>
```

### Frontend Not Loading
```bash
# Check Node.js version (need 16+)
node --version

# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### CORS Errors
- Ensure Flask API has `flask-cors` installed
- Check API is running on port 5000

---

## 📱 Mobile Access

The web UI is responsive and works on mobile devices. Access via:
```
http://<your-server-ip>:5173
```

---

## 🔐 Security Notes

⚠️ **Development Mode**: The default setup is for local development only.

For production:
1. Set `FLASK_ENV=production`
2. Use proper authentication
3. Enable HTTPS
4. Configure CORS for specific origins
5. Add rate limiting

---

## 📊 API Response Examples

### Running Session
```json
{
    "session_id": "20260325-101850",
    "status": "running",
    "task": "Build a REST API...",
    "started_at": "2026-03-25T10:18:50"
}
```

### Completed Session
```json
{
    "session_id": "20260325-101850",
    "status": "completed",
    "result": {
        "project_dir": "/path/to/project/20260325-101850",
        "build_result": { "files_created": [...] },
        "validation_result": { "success": true },
        "runtime_result": { "success": true },
        "evaluation_result": { "score": 85 }
    },
    "meta_decisions": [...]
}
```

---

## 🎨 UI Screenshots

The web interface includes:
- **Dark theme** for comfortable viewing
- **Real-time updates** every 3-5 seconds
- **Responsive design** for all screen sizes
- **Example tasks** for quick testing
- **Session history** with filtering

---

Enjoy the web interface! 🚀
