# API Fallback System - Setup Guide

## Overview

The Multi-Agent Orchestrator now supports **API-based agents** as fallbacks when CLI agents are slow or unavailable. You can configure multiple API providers (OpenRouter, Groq, Google AI, DeepSeek) and they will be used automatically when CLI agents fail.

---

## Quick Start

### 1. Add an API Key (Interactive)

```bash
cd /home/abirami/Desktop/sathi/multi/multi-agents

# Run the interactive setup
./bin/multi-api add
```

You'll be prompted for:
- Provider (openrouter, groq, google_ai, deepseek)
- Model
- Role (backend, frontend, testing, planner)
- API Key
- Agent name

### 2. Test Your API Agent

```bash
./bin/multi-api test my-api-agent
```

### 3. Run Orchestrator

API agents are **automatically used as fallback** when CLI agents fail or timeout!

```bash
./bin/multi
/run "Build a calculator"
```

---

## Supported Providers

| Provider | Free Tier | Models | Get Key |
|----------|-----------|--------|---------|
| **OpenRouter** | ✅ $1 free credit | Gemini, Llama, Mistral, Qwen | https://openrouter.ai/keys |
| **Groq** | ✅ Free tier | Llama-3.3-70B, Mixtral, Gemma | https://console.groq.com/keys |
| **Google AI** | ✅ 60 requests/min | Gemini-2.0-Flash, Gemini-1.5 | https://makersuite.google.com/app/apikey |
| **DeepSeek** | ✅ Free tier | DeepSeek-Chat, DeepSeek-Coder | https://platform.deepseek.com/api_keys |

---

## CLI Commands

### `multi-api add` - Add API Agent

**Interactive mode:**
```bash
./bin/multi-api add
# or
./bin/multi-api add --interactive
```

**Direct mode:**
```bash
./bin/multi-api add openrouter sk-or-... google/gemini-2.0-flash backend my-gemini
```

### `multi-api list` - List Configured Agents

```bash
./bin/multi-api list

Output:
Configured API Agents:
============================================================

  ✓ my-gemini
      Provider: openrouter
      Model:    google/gemini-2.0-flash
      Role:     backend
      
  ✓ groq-llama
      Provider: groq
      Model:    llama-3.3-70b-versatile
      Role:     frontend
```

### `multi-api test` - Test API Agent

```bash
./bin/multi-api test my-gemini

Output:
Testing my-gemini...
Sending test request...
✓ my-gemini is working!
  Response time: 2.34s
  Sample: def add(a, b):
      return a + b...
```

### `multi-api remove` - Remove API Agent

```bash
./bin/multi-api remove my-gemini
```

### `multi-api providers` - Show Available Providers

```bash
./bin/multi-api providers

Output:
Available API Providers:
============================================================

  openrouter
  Base URL: https://openrouter.ai/api/v1/chat/completions
  Models:
    - google/gemini-2.0-flash-001
    - meta-llama/llama-3.3-70b-instruct
    - mistralai/mistral-large
    ...
```

---

## Configuration File

API keys are stored in: `config/api_keys.json`

```json
{
  "agents": {
    "my-gemini": {
      "provider": "openrouter",
      "api_key": "sk-or-...",
      "model": "google/gemini-2.0-flash",
      "role": "backend",
      "enabled": true
    },
    "groq-llama": {
      "provider": "groq",
      "api_key": "gsk_...",
      "model": "llama-3.3-70b-versatile",
      "role": "frontend",
      "enabled": true
    }
  }
}
```

---

## How Fallback Works

### Execution Flow

```
1. Try CLI agent (e.g., gemini CLI)
   ↓ (timeout or error)
2. Try API fallback (e.g., Google AI API)
   ↓ (error)
3. Try other fallbacks from FALLBACK_MAP
   ↓ (all failed)
4. Mark task as FAILED
```

### Example Log Output

```
[task-002] Starting: Build login UI (agent: gemini)
[INFO] Running: gemini -p (prompt: 484 chars)
[20:01:21] WARNING: Attempt 1/2 timed out after 90.2s
[INFO] Retrying in 5s...
[20:02:11] WARNING: Attempt 2/2 failed
[INFO] Falling back from gemini to API agent: my-gemini
[INFO] Running: API call to openrouter (prompt: 484 chars)
[20:02:14] INFO: Task task-002 completed in 3.2s via API
```

---

## Recommended Setup

### For Best Results

Configure **multiple API fallbacks**:

```bash
# Primary fallback (OpenRouter - many models)
./bin/multi-api add openrouter sk-or-... google/gemini-2.0-flash backend openrouter-backend

# Secondary fallback (Groq - fastest)
./bin/multi-api add groq gsk_... llama-3.3-70b-versatile backend groq-fast

# Tertiary fallback (Google AI - direct)
./bin/multi-api add google_ai AIza... gemini-2.0-flash frontend google-direct
```

### Cost-Effective Setup

```bash
# Groq - completely free, very fast
./bin/multi-api add groq gsk_... llama-3.3-70b-versatile backend

# Google AI - free tier (60 req/min)
./bin/multi-api add google_ai AIza... gemini-2.0-flash frontend
```

---

## Environment Variables (Alternative)

Instead of `multi-api add`, you can use environment variables:

```bash
# In .env file
OPENROUTER_API_KEY=sk-or-...
GROQ_API_KEY=gsk_...
GOOGLE_AI_API_KEY=AIza...
DEEPSEEK_API_KEY=sk-ds-...

# Or export directly
export OPENROUTER_API_KEY=sk-or-...
```

Then create agents in code that read from environment.

---

## Troubleshooting

### "Unknown provider"

Make sure you're using a supported provider name:
- `openrouter`
- `groq`
- `google_ai`
- `deepseek`

### "API call failed"

1. Check your API key is correct
2. Verify you have credits/quota remaining
3. Test with `multi-api test <agent-name>`

### "Agent not found"

List configured agents:
```bash
./bin/multi-api list
```

### API is Slow

Try a different provider:
- **Groq** is fastest (free, ~1s responses)
- **OpenRouter** has most model options
- **Google AI** is reliable for Gemini models

---

## API Agent Roles

| Role | Used For | Recommended Models |
|------|----------|-------------------|
| **backend** | Python, Flask, APIs | Llama-3.3-70B, Gemini-2.0 |
| **frontend** | React, HTML, CSS | Gemini-2.0, Claude models |
| **testing** | Pytest, Jest | Llama-3.3-70B, DeepSeek-Coder |
| **planner** | Task decomposition | Llama-3.3-70B, Gemini-2.0 |

---

## Security Notes

⚠️ **API keys are stored in plain text** in `config/api_keys.json`

- Keep this file private
- Don't commit to git
- Use separate keys for development/production

---

## Example Session

```bash
# Setup
./bin/multi-api add
> Select provider: groq
> Select model: llama-3.3-70b-versatile
> Select role: backend
> API Key: gsk_...
> Agent name: groq-backend

# Test
./bin/multi-api test groq-backend
> ✓ groq-backend is working! (1.2s)

# Run orchestrator
./bin/multi
> /run "Build a calculator"

# Watch for fallback
[INFO] Falling back from opencode to API agent: groq-backend
[INFO] Task completed in 2.1s via API
```

---

**Version:** 1.0.0
**Date:** 2026-03-29
**Status:** ✅ Production Ready
