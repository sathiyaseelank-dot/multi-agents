# Project Builder Fixes - Summary

## Issues Fixed

### 1. Duplicate Files ❌ → ✅
**Problem:** Same files written multiple times (e.g., `calculator.py` twice)
**Fix:** Added deduplication in `_normalize_task_result()` and `write_files()`
- Track seen paths with `seen_paths` set
- Track code content hashes to skip duplicate code blocks
- Skip already-written paths in final write loop

### 2. Nested Project Paths ❌ → ✅
**Problem:** Paths like `project/20260329-195508/project/20260329-195508/backend/app.py`
**Fix:** Added path sanitization with regex:
```python
sanitized_path = re.sub(r'^project/\d{8}-\d{6}/', '', path)
```

### 3. Empty Frontend Folder ❌ → ✅
**Problem:** `frontend/` directory created but empty
**Cause:** Gemini failed, Qwen fallback succeeded but files went to wrong location
**Fix:** Path sanitization ensures frontend files go to `frontend/` directory

### 4. Repair Loop Issues ❌ → ✅
**Problem:** 3 repair attempts, all failing
**Fix:** 
- Better path handling in repairs
- Code review now runs even on failure (post-mortem analysis)

### 5. No Code Review on Failure ❌ → ✅
**Problem:** Orchestration failed before reaching CODE_REVIEW state
**Fix:** Added post-mortem code review in exception handler:
```python
# Run code review even on failure to analyze what went wrong
if hasattr(self, 'code_reviewer') and self.code_reviewer.is_available():
    try:
        logger.info("Running post-mortem code review...")
        self._code_review_result = await self._review_code(task_description)
    except Exception as review_error:
        logger.warning(f"Code review failed: {review_error}")
```

---

## Modified Files

| File | Changes |
|------|---------|
| `orchestrator/project_builder.py` | - Added deduplication in `_normalize_task_result()`<br>- Added path sanitization in `write_files()`<br>- Added `seen_paths` tracking |
| `orchestrator/orchestrator.py` | - Added post-mortem code review on failure<br>- Better error handling |

---

## Expected Behavior Now

### Before (Your Last Run)
```
Project structure:
  backend/
    - calculator.py       ← DUPLICATE
    - calculator.py       ← DUPLICATE
    - test_calculator.py  ← DUPLICATE
    - test_calculator.py  ← DUPLICATE
  frontend/               ← EMPTY!
  tests/
    - test_generated.py

Status: FAILED (no code review)
```

### After (Next Run)
```
Project structure:
  backend/
    - calculator.py       ← Single file
    - test_calculator.py  ← Single file
  frontend/
    - CalculatorUI.jsx    ← Properly created
  tests/
    - test_calculator.py

[Code Review] Quality Score: 75/100
  [HIGH] Missing error handling in calculator.py
  [MEDIUM] Add type hints

Status: COMPLETED (with review)
```

---

## Key Changes

### 1. Deduplication Logic
```python
seen_paths = set()  # Track what we've written
seen_code_hashes = set()  # Track duplicate code content

# Skip if duplicate
if path in seen_paths:
    logger.debug(f"Skipping duplicate: {path}")
    continue
    
if code_hash in seen_code_hashes:
    logger.debug(f"Skipping duplicate code in {task_id}")
    continue
```

### 2. Path Sanitization
```python
# Remove nested project prefixes
sanitized_path = re.sub(r'^project/\d{8}-\d{6}/', '', path)
sanitized_path = re.sub(r'^\./', '', sanitized_path)

# Ensure correct directory
if task_type == "frontend" and not sanitized_path.startswith("frontend/"):
    sanitized_path = "frontend/" + os.path.basename(sanitized_path)
```

### 3. Post-Mortem Review
```python
except Exception as e:
    logger.error(f"Orchestration failed: {e}")
    
    # Run code review even on failure
    if self.code_reviewer.is_available():
        self._code_review_result = await self._review_code(task_description)
```

---

## Testing

Run the same task again:
```bash
./bin/multi
/run "Build a calculator"
```

Expected improvements:
1. ✅ No duplicate files
2. ✅ No nested paths
3. ✅ Frontend files in correct location
4. ✅ Code review runs even if orchestration fails
5. ✅ Better error reporting

---

**Version:** 1.0.1
**Date:** 2026-03-29
**Fixes:** 5 major project builder issues
