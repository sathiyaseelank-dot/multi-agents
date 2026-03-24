# Frontend Worker Prompt Template (Gemini)

Used by `agents/frontend.py` — sent to `gemini -p`.

## Template

```
Write UI code for: {task_description}
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
