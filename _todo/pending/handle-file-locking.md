# Task: Handle File Locking and Permission Errors Gracefully

**Original Objective:** Handle gracefully files locked by another process and permission errors during file operations

**Status:** Proposal - Ready for Implementation

---

## Problem Analysis

### Current Behavior

The code handles `PermissionError` during file **discovery** ([gs_batch.py:380](gs_batch/gs_batch.py#L380), [gs_batch.py:392](gs_batch/gs_batch.py#L392)) but crashes during file **operations** in `move_output()`.

### Real Error Scenarios

**1. Output file locked (e.g., open in PDF viewer)**
```bash
$ gs_batch input.pdf --force
PermissionError: [Errno 13] Permission denied: 'input.pdf'
```

**2. Output directory not writable**
```bash
$ gs_batch input.pdf --prefix=readonly_dir/
PermissionError: [Errno 13] Permission denied
```

**3. Disk full**
```bash
$ gs_batch large.pdf
OSError: [Errno 28] No space left on device
```

**4. Directory creation fails**
```bash
$ gs_batch input.pdf --prefix=/root/forbidden/
PermissionError: Cannot create directory
```

### Current Architecture Problem

File operations happen **inside multiprocessing workers** ([gs_batch.py:297-298](gs_batch/gs_batch.py#L297-L298)), which:
- ❌ Cannot prompt user for retry (no TTY access)
- ❌ Cause entire batch to fail on first error
- ❌ Don't clean up temp files on error
- ❌ Show stack traces instead of user-friendly messages

---

## Solution: Hybrid Processing Architecture

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

**Precheck for locked files is unreliable and problematic:**

1. **Race Condition:** File unlocked during precheck, locked again after GS processing (minutes later)
2. **False Confidence:** User closes file for precheck, opens it again during GS processing
3. **Implementation Complexity:** Must duplicate output path logic to know what to check
4. **Platform Issues:** On Windows, only reliable lock detection is attempting actual write
5. **Wrong UX:** Forces user to deal with locks BEFORE work is done, then again if lock reappears

**Better approach:** Detect locks at actual write time, preserve GS work in temp file, allow unlimited retries.

---

## Architecture Changes

### Phase 1: Refactor Worker Function

**Current:** Workers call `process_file()` → `move_output()` → moves files

**New:** Workers call `process_file()` → returns temp file info only

**Location:** [gs_batch.py:656-731](gs_batch/gs_batch.py#L656-L731) (`process_file` function)

**Changes:**
1. Remove call to `move_output()`
2. Return dict with temp file path instead of final result
3. Include all metadata needed for phase 2

**New return format:**
```python
{
    'id': id,
    'status': 'success' | 'gs_failed',
    'original_file': pdf_file,
    'original_size': os.path.getsize(pdf_file),
    'temp_file': temp_output_file,  # Path to GS output
    'new_size': os.path.getsize(temp_output_file),
    'prefix': prefix,
    'suffix': suffix,
    'keep_smaller': keep_smaller,
    'force': force,
}
```

### Phase 2: Serial File Finalization

**Location:** After `pool.map()` in main thread ([gs_batch.py:298](gs_batch/gs_batch.py#L298))

**New processing:**
```python
try:
    with multiprocessing.Pool(initializer=init_worker) as pool:
        gs_results = pool.map(process_file, file_tasks)
except KeyboardInterrupt:
    # ... existing handler

# NEW: Process file operations serially in main thread
final_results = []
for gs_result in gs_results:
    if gs_result['status'] == 'success':
        final_result = finalize_output(gs_result)  # Can prompt user
        final_results.append(final_result)
    else:
        # GS failed - return error result
        final_results.append(create_error_result(gs_result, "Ghostscript processing failed"))

# Continue with existing table output using final_results
```

### Phase 3: New `finalize_output()` Function

**Purpose:** Move files from temp locations to final destinations with error handling and retry logic

**Location:** New function before `process_file()` (~line 655)

**Signature:**
```python
def finalize_output(gs_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Move processed file from temp location to final destination.

    Handles file locking with user prompts for retry/skip/abort.
    Runs in main thread to enable user interaction.

    Args:
        gs_result: Result dict from worker containing temp file path and metadata

    Returns:
        Final result dict for output table
    """
```

**Implementation:**
1. Extract output path logic from current `move_output()`
2. Wrap all file operations in try-except blocks
3. On `PermissionError` (file locked):
   - Prompt: "File locked. Close it, then: [R]etry / [S]kip / [A]bort"
   - Retry: Attempt operation again (unlimited retries)
   - Skip: Mark file as failed, continue with next
   - Abort: Raise exception, terminate all processing
4. On `OSError` with `ENOSPC`/`EDQUOT` (disk full):
   - Prompt: "Disk full. Free space, then: [R]etry / [S]kip / [A]bort"
   - Same retry logic
5. On other errors:
   - No retry, immediate failure with clear message
6. Always cleanup temp file (best-effort)

### Phase 4: Helper Functions

Add before `finalize_output()`:

```python
def cleanup_temp_file(temp_file: str) -> None:
    """Best-effort cleanup of temporary file."""
    try:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    except:
        pass


def create_error_result(gs_result: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Create standardized error result dict for output table."""
    return {
        "id": gs_result['id'],
        "filename": os.path.abspath(gs_result['original_file']),
        "original_size": gs_result['original_size'],
        "message": f"ERROR: {message}",
    }


def is_recoverable_error(e: Exception) -> bool:
    """Check if error is recoverable and should prompt for retry."""
    import errno

    # File locked by another process
    if isinstance(e, PermissionError):
        return True

    # Disk full or quota exceeded
    if isinstance(e, OSError) and e.errno in (errno.ENOSPC, errno.EDQUOT):
        return True

    return False


def get_error_suggestion(e: Exception) -> str:
    """Get user-friendly suggestion for error resolution."""
    import errno

    if isinstance(e, PermissionError):
        return "Close the file in any PDF viewers or other applications"

    if isinstance(e, OSError):
        if e.errno == errno.ENOSPC:
            return "Free up disk space"
        elif e.errno == errno.EDQUOT:
            return "Increase disk quota or free up space"

    return "Check file permissions and available disk space"


def prompt_retry_skip_abort(filename: str, error: Exception) -> str:
    """
    Prompt user for action on recoverable error.

    Returns: 'retry' | 'skip' | 'abort'
    """
    click.secho(f"\nError processing '{os.path.basename(filename)}':", fg="yellow")
    click.echo(f"  {error}")

    suggestion = get_error_suggestion(error)
    if suggestion:
        click.echo(f"  Suggestion: {suggestion}")

    response = click.prompt(
        "Action?",
        type=click.Choice(['r', 's', 'a'], case_sensitive=False),
        default='r',
        show_choices=True,
        show_default=True
    )

    action_map = {'r': 'retry', 's': 'skip', 'a': 'abort'}
    return action_map[response.lower()]


class AbortBatchProcessing(Exception):
    """Exception raised when user chooses to abort batch processing."""
    pass
```

### Phase 5: Summary Report

**Location:** After results table ([gs_batch.py:325](gs_batch/gs_batch.py#L325))

**Add:**
```python
# Summary statistics
total_files = len(final_results)
successful_files = sum(1 for r in final_results if 'message' not in r)
failed_files = total_files - successful_files

if failed_files > 0:
    click.secho(
        f"\nProcessed {successful_files} of {total_files} files successfully. "
        f"{failed_files} file(s) failed.",
        fg="yellow" if successful_files > 0 else "red"
    )
else:
    click.secho(f"\nAll {total_files} file(s) processed successfully.", fg="green")
```

### Phase 6: Abort Exception Handling

**Location:** [gs_batch.py:296-304](gs_batch/gs_batch.py#L296-L304)

**Add after KeyboardInterrupt handler:**
```python
except AbortBatchProcessing as e:
    click.secho(f"\nBatch processing aborted by user: {e}", fg="red")
    sys.exit(1)
```

---

## Detailed `finalize_output()` Implementation

```python
def finalize_output(gs_result: Dict[str, Any]) -> Dict[str, Any]:
    """Move processed file from temp location to final destination."""

    id = gs_result['id']
    original_file = gs_result['original_file']
    original_size = gs_result['original_size']
    temp_file = gs_result['temp_file']
    new_size = gs_result['new_size']
    prefix = gs_result['prefix']
    suffix = gs_result['suffix']
    keep_smaller = gs_result['keep_smaller']
    force = gs_result['force']

    # Calculate output path (extracted from current move_output logic)
    root = os.path.dirname(original_file)
    input_basename = os.path.splitext(os.path.basename(original_file))[0]
    input_ext = os.path.splitext(os.path.basename(original_file))[1]

    if prefix:
        # Extract directory from prefix if it contains path separators
        prefix_dir = os.path.dirname(prefix)
        prefix_name = os.path.basename(prefix)
        output_dir = os.path.join(root, prefix_dir) if prefix_dir else root
        output_file = os.path.join(output_dir, f"{prefix_name}{input_basename}{suffix}{input_ext}")
    else:
        output_file = os.path.join(root, f"{input_basename}{suffix}{input_ext}")

    overwriting = os.path.abspath(output_file) == os.path.abspath(original_file)

    # Determine which file to keep
    if new_size < original_size:
        keeping = "new" if keep_smaller else "original"
    else:
        keeping = "original"

    # Create output directory if needed
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir, exist_ok=True)
        except (PermissionError, OSError) as e:
            cleanup_temp_file(temp_file)
            return create_error_result(gs_result, f"Cannot create directory '{output_dir}': {e}")

    # File operation with retry logic
    try:
        match (keeping, overwriting):
            case ("original", True):
                # Keep original, remove temp
                cleanup_temp_file(temp_file)

            case ("original", False):
                # Copy original to output, remove temp
                retry_file_operation(
                    lambda: shutil.copy(original_file, output_file),
                    output_file,
                    "copy"
                )
                cleanup_temp_file(temp_file)

            case ("new", True):
                # Overwrite original with new
                if force:
                    retry_file_operation(
                        lambda: shutil.move(temp_file, output_file),
                        output_file,
                        "overwrite"
                    )
                else:
                    # This should not happen (already handled in main), but safety check
                    click.echo(f"Skipping overwrite for {output_file} (no --force)")
                    keeping = "original"
                    cleanup_temp_file(temp_file)

            case ("new", False):
                # Move new to output directory
                retry_file_operation(
                    lambda: shutil.move(temp_file, output_file),
                    output_file,
                    "move"
                )

    except AbortBatchProcessing:
        cleanup_temp_file(temp_file)
        raise  # Re-raise to stop all processing

    except Exception as e:
        # Unrecoverable error after retries or user skip
        cleanup_temp_file(temp_file)
        return create_error_result(gs_result, str(e))

    # Success - return result for table
    return {
        "id": id,
        "filename": os.path.abspath(output_file),
        "original_size": original_size,
        "new_size": new_size if keeping == "new" else original_size,
        "ratio": new_size / original_size if keeping == "new" else 1.0,
        "keeping": keeping,
    }


def retry_file_operation(operation: Callable, filename: str, op_type: str) -> None:
    """
    Execute file operation with unlimited retry on recoverable errors.

    Args:
        operation: Callable that performs the file operation
        filename: Filename for error messages
        op_type: Type of operation for error messages ('copy', 'move', 'overwrite')

    Raises:
        AbortBatchProcessing: If user chooses to abort
        Exception: If user chooses to skip or non-recoverable error occurs
    """
    while True:
        try:
            operation()
            return  # Success

        except (PermissionError, OSError) as e:
            if is_recoverable_error(e):
                action = prompt_retry_skip_abort(filename, e)

                if action == 'retry':
                    continue  # Loop to retry
                elif action == 'skip':
                    raise Exception(f"Skipped by user: {e}")
                else:  # abort
                    raise AbortBatchProcessing(f"User aborted on {op_type} error: {e}")
            else:
                # Non-recoverable error
                raise Exception(f"Cannot {op_type} file '{filename}': {e}")
```

---

## Performance Impact Analysis

### Current (Parallel Everything)
- Ghostscript: 5-30 seconds per file (in parallel)
- File moves: ~0.001-0.2 seconds per file (in parallel)
- **Total for 5x 10MB files:** ~5-30 seconds

### New (Hybrid Approach)
- Ghostscript: 5-30 seconds per file (still parallel)
- File moves: ~0.005-1 second total (serial, but fast)
- **Total for 5x 10MB files:** ~5-31 seconds

**Performance impact: <1 second added (0.5-3% overhead)**

File operations are ~100-1000x faster than Ghostscript processing, so serializing them has negligible impact.

---

## Testing Strategy

### Automated Tests

Add to `tests/test_gsb.py`:

```python
import errno
from unittest.mock import patch, MagicMock, call

def test_file_locked_with_retry(setup_test_files, monkeypatch):
    """Test retry logic when output file is locked."""
    # Mock user choosing 'retry' then 'skip'
    responses = iter(['r', 's'])
    monkeypatch.setattr('click.prompt', lambda *args, **kwargs: next(responses))

    # First call fails, second call fails again
    with patch('shutil.move', side_effect=PermissionError("[Errno 13] Permission denied")):
        result = runner.invoke(cli, ["tests/assets/originals/file_1.pdf", "--force"])

        assert result.exit_code == 0
        assert "Error processing" in result.output
        assert "Skipped by user" in result.output or "ERROR" in result.output


def test_file_locked_with_abort(setup_test_files, monkeypatch):
    """Test abort on file lock."""
    monkeypatch.setattr('click.prompt', lambda *args, **kwargs: 'a')

    with patch('shutil.move', side_effect=PermissionError("[Errno 13] Permission denied")):
        result = runner.invoke(cli, ["tests/assets/originals/file_1.pdf", "--force"])

        assert result.exit_code == 1
        assert "aborted" in result.output.lower()


def test_disk_full_with_retry(setup_test_files, monkeypatch):
    """Test retry prompt on disk full error."""
    disk_full_error = OSError(errno.ENOSPC, "No space left on device")

    # Mock user choosing 'skip'
    monkeypatch.setattr('click.prompt', lambda *args, **kwargs: 's')

    with patch('shutil.move', side_effect=disk_full_error):
        result = runner.invoke(cli, ["tests/assets/originals/file_1.pdf", "--force"])

        assert "Free up disk space" in result.output
        assert "Skipped" in result.output or "ERROR" in result.output


def test_directory_creation_fails(setup_test_files):
    """Test graceful handling when directory creation fails."""
    with patch('os.makedirs', side_effect=PermissionError("Cannot create")):
        result = runner.invoke(cli, [
            "tests/assets/originals/file_1.pdf",
            "--prefix=nested/path/"
        ])

        assert result.exit_code == 0
        assert "ERROR" in result.output
        assert "Cannot create directory" in result.output


def test_batch_with_mixed_failures(setup_test_files, monkeypatch):
    """Test batch processing continues after individual failures."""
    # Mock user choosing 'skip' for locked file
    monkeypatch.setattr('click.prompt', lambda *args, **kwargs: 's')

    # Make only file_2 fail with lock
    original_move = shutil.move
    def selective_fail(src, dst):
        if 'file_2' in dst:
            raise PermissionError("Locked")
        return original_move(src, dst)

    with patch('shutil.move', side_effect=selective_fail):
        result = runner.invoke(cli, [
            "tests/assets/originals/file_1.pdf",
            "tests/assets/originals/file_2.pdf",
            "tests/assets/originals/file_3.pdf",
            "--force"
        ])

        assert result.exit_code == 0
        assert "2 of 3 files successfully" in result.output or "Processed 2" in result.output
```

### Manual Testing

1. **Test locked file with retry:**
   - Open `test.pdf` in Adobe Reader
   - Run: `gs_batch test.pdf --force`
   - Verify: Prompt appears after GS processing
   - Close file, press 'R'
   - Verify: File successfully moved

2. **Test batch with mixed locks:**
   - Open `file2.pdf` in viewer
   - Run: `gs_batch --compress file1.pdf file2.pdf file3.pdf --force`
   - Verify: file1 and file3 process successfully
   - Verify: Prompt appears for file2
   - Close file2, retry
   - Verify: All 3 files complete

3. **Test abort:**
   - Lock a file
   - Run batch processing
   - When prompted, press 'A'
   - Verify: Processing stops, temp files cleaned up

4. **Test disk full simulation:**
   ```bash
   # Create small loopback filesystem (Linux)
   dd if=/dev/zero of=small.img bs=1M count=10
   mkfs.ext4 small.img
   mkdir mnt
   sudo mount -o loop small.img mnt

   gs_batch large.pdf --prefix=mnt/
   # Verify retry prompt with disk full message
   ```

---

## Implementation Checklist

### Phase 1: Refactor Worker Function
- [ ] Modify `process_file()` to return temp file info instead of calling `move_output()`
- [ ] Update return dict format with all needed metadata
- [ ] Test that workers still process files correctly

### Phase 2: Main Thread File Processing
- [ ] Add serial file finalization loop after `pool.map()`
- [ ] Update results variable names (`gs_results` → `final_results`)
- [ ] Ensure table output uses final results

### Phase 3: Implement `finalize_output()`
- [ ] Extract output path logic from current `move_output()`
- [ ] Implement file operation cases (4 branches)
- [ ] Add error handling for each operation
- [ ] Return proper result dict format

### Phase 4: Add Helper Functions
- [ ] `cleanup_temp_file()`
- [ ] `create_error_result()`
- [ ] `is_recoverable_error()`
- [ ] `get_error_suggestion()`
- [ ] `prompt_retry_skip_abort()`
- [ ] `retry_file_operation()`
- [ ] `AbortBatchProcessing` exception class

### Phase 5: Summary Report
- [ ] Add success/failure statistics calculation
- [ ] Add color-coded summary message

### Phase 6: Exception Handling
- [ ] Add `AbortBatchProcessing` handler in main thread
- [ ] Ensure temp files are cleaned on abort

### Phase 7: Testing
- [ ] Add 5 automated tests to `tests/test_gsb.py`
- [ ] Run manual testing scenarios (4 scenarios)
- [ ] Test on Windows (primary target for file locking)

### Phase 8: Cleanup
- [ ] Remove old `move_output()` function (no longer used)
- [ ] Update any comments/docstrings referencing old architecture
- [ ] Run full test suite

---

## Risk Assessment

**Low Risk Changes:**
- All changes are architectural refactoring, no algorithm changes
- Ghostscript processing logic unchanged
- CLI interface unchanged
- Backward compatible

**Potential Issues:**
- Multiprocessing might require careful handling of shared state (none currently shared)
- Temp file cleanup needs to be thorough to avoid disk space issues
- User prompts must be clear and actionable

**Mitigation:**
- Workers remain stateless (no shared state issues)
- Best-effort cleanup in all error paths
- Clear error messages with specific suggestions

---

## Expected Behavior

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

Finalizing file1.pdf... ✓
Finalizing file2_locked.pdf...

Error processing 'file2_locked.pdf':
  [Errno 13] Permission denied
  Suggestion: Close the file in any PDF viewers or other applications
Action? [r/s/a] (r): r

Finalizing file2_locked.pdf... ✓
Finalizing file3.pdf... ✓

 # | Original   | New       | Ratio | Keeping | Filename
 0 |   1.2 MB   |  850 KB   |  71%  | new     | file1.pdf
 1 |   2.3 MB   |  1.6 MB   |  70%  | new     | file2_locked.pdf
 2 |   3.5 MB   |  2.1 MB   |  60%  | new     | file3.pdf

All 3 file(s) processed successfully.
Total time: 8.45 seconds
```

---

## Implementation Estimate

- **Files Modified:**
  - `gs_batch/gs_batch.py` (main changes)
  - `tests/test_gsb.py` (new tests)

- **Lines Changed:**
  - Remove: ~95 lines (`move_output()` function)
  - Add: ~200 lines (helper functions + `finalize_output()` + main thread logic)
  - Modify: ~10 lines (worker return + main loop)
  - Net: +105 lines

- **Test Coverage:** +5 test cases

- **Implementation Time:** 2-3 hours

- **Testing Time:** 1 hour

---

## Ready for Implementation

All design decisions resolved:
✅ No precheck (detect locks at actual write time)
✅ Hybrid architecture (parallel GS, serial file ops)
✅ Unlimited retries with clear prompts
✅ Preserves GS work in temp files
✅ Minimal performance impact (<1 second)
✅ Clean error handling and reporting
✅ Comprehensive test coverage

**Next step:** Create feature branch and implement.
