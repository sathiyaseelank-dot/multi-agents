# Testing Worker Prompt Template (Kilo)

Used by `agents/tester.py` — sent to `kilo run --auto`.

## Template

```
Write tests for: {task_description}
{context_section}
Put test code in fenced blocks with language tags.
```

## Context Section (injected when dependencies are complete)

Includes actual code snippets from upstream tasks so the tester can write
tests that reference real function names and APIs:

```
Context:
Project: <epic description>
Code to test:
  - <task title>: <summary>
  ```python
  <actual code from upstream task>
  ```
```
