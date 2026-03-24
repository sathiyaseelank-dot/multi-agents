# Backend Worker Prompt Template (OpenCode)

Used by `agents/backend.py` — sent to `opencode run`.

## Template

```
Write code for: {task_description}
{context_section}
Put code in fenced blocks with language tags.
```

## Context Section (injected when dependencies are complete)

```
Context:
Project: <epic description>
Previously completed work:
  - <task title>: <summary>
Existing files: <file list>
```
