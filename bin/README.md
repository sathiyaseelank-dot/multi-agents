# Multi-Agent Interactive CLI

**Chat with AI agents directly in your terminal** - like Gemini CLI or Codex CLI.

---

## Quick Start

### Run Immediately (No Installation)

```bash
cd /home/abirami/Desktop/sathi/multi/multi-agents
./bin/multi
```

### Install for Easy Access

```bash
# Add to your PATH
echo 'export PATH="$HOME/Desktop/sathi/multi/multi-agents/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Now you can run from anywhere
multi
```

---

## Features

- 💬 **Interactive chat** with AI agents
- 🤖 **Multiple agents** - Codex, OpenCode, Gemini, Kilo
- 🎨 **Color-coded output** for easy reading
- 📝 **Conversation history** - save and review
- ⚡ **Switch agents** mid-conversation
- 🔧 **Slash commands** for control
- ⚡ **Real-time streaming** - Watch AI output as it's generated (like ChatGPT)
- 🎯 **Animated thinking indicator** - Visual feedback while AI processes
- ⏱️ **Response timing** - See how long each response took

---

## Interface

```
============================================================
  Multi-Agent CLI v0.3.0
  Interactive AI Development Assistant
============================================================

Available Agents:
  ✓ codex        - Planner: Plan & decompose tasks
  ✓ opencode     - Backend: Backend code generation
  ✓ gemini       - Frontend: Frontend code generation
  ✓ kilo         - Tester: Test generation

Commands:
  /help       - Show this help
  /agent <name> - Switch agent (codex, opencode, gemini, kilo)
  /agents     - List available agents
  /clear      - Clear conversation history
  /save <file> - Save conversation to file
  /quit       - Exit

============================================================

codex » Plan a REST API with user authentication
```

---

## Usage Examples

### Chat with Codex (Planner)

```
codex » Build a login system with JWT authentication

Thinking...
----------------------------------------
Epic: Build a login system with JWT authentication

Tasks (5):
  1. [opencode] Set up Flask application structure
  2. [opencode] Create user database models
  3. [opencode] Implement JWT authentication endpoints
  4. [gemini] Build login UI components
  5. [kilo] Write authentication tests

Phases: 3
  Phase 1: 2 tasks
  Phase 2: 2 tasks
  Phase 3: 1 task
----------------------------------------
```

### Chat with OpenCode (Backend)

```
opencode » Create a Flask endpoint for user login

Thinking...
----------------------------------------
Code Block 1 (python):
  from flask import Blueprint, request, jsonify
  from werkzeug.security import check_password_hash
  import jwt
  
  @bp.route('/login', methods=['POST'])
  def login():
      data = request.get_json()
      user = User.query.filter_by(username=data['username']).first()
      
      if not user or not check_password_hash(user.password, data['password']):
          return jsonify({'error': 'Invalid credentials'}), 401
      
      token = jwt.encode({'user_id': user.id}, app.config['SECRET_KEY'])
      return jsonify({'token': token})
----------------------------------------
```

### Chat with Gemini (Frontend)

```
gemini » Create a React login form component

Thinking...
----------------------------------------
Code Block 1 (jsx):
  import React, { useState } from 'react';
  
  function LoginForm({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    
    const handleSubmit = async (e) => {
      e.preventDefault();
      const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      // ...
    };
    
    return (
      <form onSubmit={handleSubmit}>
        <input value={username} onChange={e => setUsername(e.target.value)} />
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} />
        <button type="submit">Login</button>
      </form>
    );
  }
----------------------------------------
```

### Chat with Kilo (Testing)

```
kilo » Write tests for the login endpoint

Thinking...
----------------------------------------
Code Block 1 (python):
  import pytest
  
  def test_login_success(client, test_user):
      response = client.post('/api/login', json={
          'username': 'testuser',
          'password': 'password123'
      })
      assert response.status_code == 200
      assert 'token' in response.json
  
  def test_login_invalid_credentials(client):
      response = client.post('/api/login', json={
          'username': 'testuser',
          'password': 'wrongpassword'
      })
      assert response.status_code == 401
----------------------------------------
```

---

## Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help message |
| `/agent <name>` | Switch to different agent |
| `/stream` | Toggle real-time streaming on/off |
| `/stream on` | Enable streaming mode (default) |
| `/stream off` | Wait for complete response |
| `/run [task]` | Run the full orchestrator pipeline |
| `/agents` | List all available agents |
| `/clear` | Clear conversation history |
| `/save <file>` | Save conversation to file |
| `/history` | Show conversation history |
| `/quit` or `/exit` | Exit the CLI |

---

## Streaming Mode

By default, streaming is **enabled**. You'll see AI output appear in real-time as it's generated.

### Example with Streaming

```
codex » Plan a REST API with user authentication

⠋ Thinking...
⠙ Thinking...
⠹ Thinking...
✓ Done!

⚡ Streaming from codex...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Let me break down this request for a REST API with authentication...

I'll design a clean API structure with:
- User registration and login endpoints
- JWT-based authentication
- Refresh token rotation
- Password reset flow

Here's the task breakdown:

```json
{
  "epic": "REST API with user authentication",
  "tasks": [
    {
      "id": "task-001",
      "agent": "opencode",
      "title": "Set up Flask application",
      ...
    }
  ]
}
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Done in 8.2s
```

### Toggle Streaming

```
/stream off
✓ Streaming disabled - Will wait for complete responses

codex » Plan a login system
Thinking...
[waits for complete response]
[shows full response at once]

/stream on
✓ Streaming enabled - You'll see AI output in real-time
```

---

## Full Pipeline Execution

Use `/run` to execute the complete orchestrator pipeline:

```
/run "Build a login system with JWT authentication"

============================================================
  Running Full Orchestrator Pipeline
============================================================

This will:
  1. Plan tasks with Codex
  2. Execute backend tasks with OpenCode
  3. Execute frontend tasks with Gemini
  4. Write tests with Kilo
  5. Generate code files in output/

Executing: python3 orchestrator/main.py "Build a login system..."
────────────────────────────────────────────────────────────────

[Orchestrator output streams here...]

✓ Orchestrator completed successfully!
```

This runs the same orchestrator as the command-line, with:
- DAG-based parallel execution
- Agent fallback on failures
- Checkpoint/resume capability
- Code generation to `output/`

---

## Switching Agents

```
codex » Plan a user registration system

[Gets plan back]

/agent opencode

✓ Switched to opencode (Backend)
  Backend code generation

opencode » Now create the Flask models for user registration

[Gets code back]

/agent kilo

✓ Switched to kilo (Tester)
  Test generation

kilo » Write tests for the registration endpoint
```

---

## Saving Conversations

```
codex » /save conversation-plan.txt

✓ Conversation saved to conversation-plan.txt
```

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Ctrl+C` | Cancel current request |
| `Ctrl+D` | Exit CLI |
| `Enter` | Send message |

---

## Troubleshooting

### No Agents Available

```
✗ Not installed - Install the agent CLI:
  - Codex: https://github.com/openai/codex
  - OpenCode: https://github.com/opencode-ai/opencode
  - Gemini: https://github.com/google/gemini-cli
  - Kilo: https://github.com/kilo-ai/kilo
```

### Import Errors

```bash
# Ensure you're in the project directory
cd /home/abirami/Desktop/sathi/multi/multi-agents

# Or set PYTHONPATH
export PYTHONPATH="$PWD:$PYTHONPATH"
```

### Permission Denied

```bash
chmod +x bin/multi
```

---

## Comparison with Other CLIs

| Feature | Multi-Agent CLI | Gemini CLI | Codex CLI |
|---------|----------------|------------|-----------|
| Multiple agents | ✅ 4 agents | ❌ 1 agent | ❌ 1 agent |
| Switch agents | ✅ Mid-chat | ❌ No | ❌ No |
| Specialized roles | ✅ Planner, Backend, Frontend, Tester | ✅ General | ✅ General |
| Conversation history | ✅ Save & review | ⚠️ Session only | ⚠️ Session only |
| Open source | ✅ MIT | ⚠️ Varies | ⚠️ Varies |

---

## Version

**CLI Version:** 1.0.0
**Orchestrator Version:** 0.3.0

---

## License

MIT License
