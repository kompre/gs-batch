# Task: Handle File Locking and Permission Errors Gracefully

**Original Objective:** Handle gracefully files locked by another process and permission errors during file operations

**Status:** Completed

**Completion Date:** 2025-10-17

**Branch:** `feature/handle-file-locking` (merged to `main`)

**Commits:**
- 461c0b0 - Initial proposal documentation
- 95bdd87 - Core implementation of hybrid architecture
- d05b362 - Improved error prompt clarity
- d100bbf - Added 5 automated tests
- 2e94273 - Merge to main

---

## Final Implementation Summary

Successfully implemented graceful file locking and permission error handling using a hybrid processing architecture.

### Key Features Delivered

1. **Hybrid Architecture**
   - Parallel Ghostscript processing in workers (CPU-intensive)
   - Serial file operations in main thread (enables user interaction)
   - Performance impact: <1 second overhead (negligible)

2. **User-Friendly Error Handling**
   - Retry/Skip/Abort prompts for recoverable errors (file locks, disk full)
   - Unlimited retry capability without re-running Ghostscript
   - Clear error messages with actionable suggestions
   - Batch processing continues after individual file failures

3. **Preserved Expensive Work**
   - GS output saved in temp files during error recovery
   - Temp file cleanup in all error paths (best-effort)
   - No loss of processing work during retry

4. **Summary Reporting**
   - Success/failure statistics at end of batch
   - Color-coded output (green/yellow/red)

### Implementation Details

**Modified Files:**
- `gs_batch/gs_batch.py`: +382 lines added, -257 lines removed (net +125 lines)
- `tests/test_gsb.py`: +157 lines added
- `_todo/pending/handle-file-locking.md`: Task documentation

**New Functions Added:**
1. `AbortBatchProcessing` - Exception class for user abort
2. `cleanup_temp_file()` - Best-effort temp file cleanup
3. `create_error_result()` - Standardized error result formatting
4. `is_recoverable_error()` - Detects errors that allow retry
5. `get_error_suggestion()` - User-friendly error resolution hints
6. `prompt_retry_skip_abort()` - Interactive user prompt with clear options
7. `retry_file_operation()` - Unlimited retry wrapper for file operations
8. `finalize_output()` - Main file finalization with error handling

**Refactored Functions:**
- `process_file()` - Now returns temp file metadata instead of moving files
- Main processing loop - Added serial finalization phase after parallel GS processing

**Removed Functions:**
- `move_output()` - Replaced by `finalize_output()` with better error handling

### Test Coverage

**All 15 tests passing:**
- 10 original tests (unchanged)
- 5 new error handling tests:
  - `test_file_locked_with_skip` - File lock with user skip
  - `test_file_locked_with_abort` - File lock with user abort
  - `test_disk_full_with_skip` - Disk full with user skip
  - `test_directory_creation_fails` - Directory creation permission error
  - `test_batch_with_mixed_failures` - Batch continues after individual failures

**Testing Methodology:**
- `unittest.mock` for simulating file system errors
- `monkeypatch` for simulating user responses
- Selective failure simulation for batch testing
- errno constants (ENOSPC, EDQUOT) for disk full scenarios

**Manual Testing:**
- Confirmed on Windows with locked PDF files
- User verified prompt clarity and retry functionality

---

## Problem Analysis (Original)

### Current Behavior (Before)

Code handled `PermissionError` during file discovery but crashed during file operations in `move_output()`.

**Error Scenarios:**
1. Output file locked (e.g., open in PDF viewer) → crash
2. Output directory not writable → crash
3. Disk full → crash
4. Directory creation fails → crash

**Architecture Problem:**
File operations happened inside multiprocessing workers, which:
- ❌ Cannot prompt user for retry (no TTY access)
- ❌ Cause entire batch to fail on first error
- ❌ Don't clean up temp files on error
- ❌ Show stack traces instead of user-friendly messages

---

## Solution Design

### Core Strategy

**Separate expensive CPU work from lightweight file operations:**

1. **Phase 1 (Parallel):** Ghostscript processing in worker pool
   - CPU-intensive: 5-30 seconds per file
   - Workers write to temp files
   - Workers return temp file paths + metadata
   - No file system interactions with final destinations

2. **Phase 2 (Serial):** File finalization in main thread
   - Lightweight: <1 second total for all files
   - Move/copy temp files to final destinations
   - Can prompt user for retry on errors
   - Clean error handling and reporting

### Why No Precheck

**Precheck for locked files is unreliable:**
1. **Race Condition:** File unlocked during precheck, locked again after GS processing
2. **False Confidence:** User closes file for precheck, opens it during GS processing
3. **Platform Issues:** Windows only reliably detects locks on actual write attempt
4. **Wrong UX:** Forces user to deal with locks BEFORE work is done

**Better approach:** Detect locks at actual write time, preserve GS work in temp file, allow unlimited retries.

---

## Performance Impact

### Benchmarking

**Current (Parallel Everything):**
- Ghostscript: 5-30 seconds per file (parallel)
- File moves: ~0.001-0.2 seconds per file (parallel)
- **Total for 5x 10MB files:** ~5-30 seconds

**New (Hybrid Approach):**
- Ghostscript: 5-30 seconds per file (still parallel)
- File moves: ~0.005-1 second total (serial)
- **Total for 5x 10MB files:** ~5-31 seconds

**Performance impact: <1 second added (0.5-3% overhead)**

File operations are ~100-1000x faster than Ghostscript processing, so serializing them has negligible impact.

---

## User Experience Improvements

### Before
```
$ gs_batch --compress file1.pdf file2_locked.pdf file3.pdf --force

Processing 3 files...
[Progress bars for file1, file2, file3]
Traceback (most recent call last):
  ...
PermissionError: [Errno 13] Permission denied: 'file2_locked.pdf'
```

### After
```
$ gs_batch --compress file1.pdf file2_locked.pdf file3.pdf --force

Processing 3 files...
[Progress bars for all 3 files complete]

Error processing 'file2_locked.pdf':
  [Errno 13] Permission denied
  Suggestion: Close the file in any PDF viewers or other applications

Available actions:
  [r]etry  - Try the operation again (after fixing the issue)
  [s]kip   - Skip this file and continue with the next one
  [a]bort  - Stop processing all files and exit

Choose action [r/s/a] (r): r

 # | Original   | New       | Ratio | Keeping | Filename
 0 |   1.2 MB   |  850 KB   |  71%  | new     | file1.pdf
 1 |   2.3 MB   |  1.6 MB   |  70%  | new     | file2_locked.pdf
 2 |   3.5 MB   |  2.1 MB   |  60%  | new     | file3.pdf

All 3 file(s) processed successfully.
```

---

## Technical Insights

### Design Decision: Hybrid Architecture

**Initial Consideration:** Move all file operations to precheck phase
**Problem:** Race conditions, false confidence, poor UX
**Solution:** Detect errors at actual operation time, allow unlimited retries

**Key Insight:** File operations are so fast relative to GS processing that serializing them has no meaningful performance impact, but enables critical UX improvements (user prompts).

### Error Recovery Pattern

**Recoverable Errors:**
- `PermissionError` (file locked)
- `OSError` with `errno.ENOSPC` (disk full)
- `OSError` with `errno.EDQUOT` (quota exceeded)

**Non-Recoverable Errors:**
- Other `OSError` variants
- Directory creation failures (fail immediately)

**Retry Logic:**
- Unlimited retries for recoverable errors
- Temp file preserved during retry
- User can abort entire batch at any time

### Cleanup Strategy

**Best-Effort Cleanup:**
```python
def cleanup_temp_file(temp_file: str) -> None:
    try:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    except:
        pass  # Best effort - don't cascade errors
```

**Rationale:** If temp cleanup fails, don't cascade the error and mask the original problem. Temp files will be cleaned by OS eventually.

---

## Code Quality Improvements

### Match/Case Pattern for File Operations

Used Python 3.10+ match/case for clear branching logic:
```python
match (keeping, overwriting):
    case ("original", True):
        cleanup_temp_file(temp_file)
    case ("original", False):
        retry_file_operation(lambda: shutil.copy(...))
    case ("new", True):
        retry_file_operation(lambda: shutil.move(...))
    case ("new", False):
        retry_file_operation(lambda: shutil.move(...))
```

### Type Hints

Added comprehensive type hints for new functions:
- `Dict[str, Any]` for result dictionaries
- `Callable` for operation wrappers
- Return type documentation in docstrings

### Error Message Quality

- Specific error types with actionable suggestions
- Color-coded output (yellow for warnings, red for errors, green for success)
- File basenames in prompts (not full paths) for readability

---

## Lessons Learned

1. **Multiprocessing + User Interaction Don't Mix**
   - Worker processes cannot prompt users (no TTY)
   - Solution: Separate interactive operations to main thread

2. **Performance Asymmetry is Powerful**
   - When one operation dominates (GS: 30s vs file ops: 0.1s), you can serialize the fast part to gain other benefits (user interaction)

3. **Precheck is Often Wrong**
   - Race conditions, false confidence, platform issues
   - Better: Detect at actual operation time, allow retry

4. **Best-Effort Cleanup is OK**
   - Don't cascade cleanup errors
   - OS will eventually clean temp files

5. **Clear User Prompts Matter**
   - Original `(r,s,a)` was unclear
   - New format with explanations much better:
     ```
     Available actions:
       [r]etry  - Try the operation again (after fixing the issue)
       [s]kip   - Skip this file and continue with the next one
       [a]bort  - Stop processing all files and exit
     ```

---

## Future Enhancements (Optional)

1. **Configurable Retry Limit**
   - Currently unlimited retries
   - Could add `--max-retries N` option

2. **Auto-Retry with Backoff**
   - For transient errors (disk full), auto-retry with exponential backoff
   - Prompt only after N failed attempts

3. **Progress Persistence**
   - Save batch state to resume after abort
   - Useful for very large batches

4. **Parallel File Operations**
   - Could use asyncio for parallel file ops while maintaining main thread prompts
   - Complexity may not be worth it given file ops are already fast

---

## Completion Checklist

✅ Modify `process_file()` to return temp file info
✅ Add serial file finalization loop after `pool.map()`
✅ Implement `finalize_output()` with output path logic
✅ Add 7 helper functions
✅ Add success/failure summary statistics
✅ Add `AbortBatchProcessing` exception handler
✅ Add 5 automated tests
✅ Manual testing on Windows with locked files
✅ Improve prompt clarity based on user feedback
✅ Remove old `move_output()` function
✅ Run full test suite (15/15 passing)
✅ Merge to main branch

---

## Related Documentation

- Original proposal: `_todo/proposal/handle-file-locking.md` (now deleted)
- Main implementation: `gs_batch/gs_batch.py:782-1003`
- Test suite: `tests/test_gsb.py:385-539`

---

**Task completed successfully with comprehensive testing and user validation.**
