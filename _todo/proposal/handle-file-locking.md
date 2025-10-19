# Task: Handle File Locking and Permission Errors Gracefully

**Original Objective:** Handle gracefully files locked by another process and permission errors during file operations

**Status:** Proposal - Awaiting User Approval

---

## Problem Analysis

### Current Behavior

The code currently handles `PermissionError` when **reading** directories during file discovery:
- **Line 380:** Catching `PermissionError` during recursive walk
- **Line 392:** Catching `PermissionError` during directory listing

However, it **does NOT handle errors when writing/moving output files**, leading to crashes in these scenarios:
1. Output file is locked by another process (e.g., open in PDF viewer)
2. Output directory is not writable (permission issues)
3. Temp file cannot be moved to destination (various OS errors)
4. Disk is full or quota exceeded
5. Invalid output path characters on Windows

### Error Scenarios Demonstrated

**Scenario 1: File Open in PDF Viewer**
```bash
# User has output.pdf open in Acrobat Reader
$ gs_batch input.pdf --force --prefix=output

Traceback (most recent call last):
  File "gs_batch.py", line 419, in move_output
    shutil.move(temp_file, output_file)
PermissionError: [Errno 13] Permission denied: 'output.pdf'
```

**Scenario 2: Read-Only Output Directory**
```bash
$ chmod 555 output_dir/
$ gs_batch input.pdf --prefix=output_dir/

Traceback (most recent call last):
  File "gs_batch.py", line 428, in move_output
    shutil.move(temp_file, 'output_dir/input.pdf')
PermissionError: [Errno 13] Permission denied
```

**Scenario 3: Disk Full**
```bash
$ gs_batch large_file.pdf

OSError: [Errno 28] No space left on device
```

### Code Locations Requiring Error Handling

**File:** `gs_batch/gs_batch.py`

**Function:** `move_output()` (lines 348-445)

**Vulnerable Operations:**

1. **Line ~399:** Directory creation
   ```python
   os.makedirs(output_dir, exist_ok=True)
   # Can fail: PermissionError, OSError
   ```

2. **Line 414:** Copy original file
   ```python
   shutil.copy(original_file, output_file)
   # Can fail: PermissionError, OSError, FileExistsError
   ```

3. **Line 419:** Overwrite original file
   ```python
   shutil.move(temp_file, output_file)
   # Can fail: PermissionError, OSError (file locked)
   ```

4. **Line 428:** Move new file to output
   ```python
   shutil.move(temp_file, output_file)
   # Can fail: PermissionError, OSError
   ```

5. **Line 407, 415, 420, 429:** Temp file cleanup
   ```python
   os.remove(temp_file)
   # Can fail: PermissionError, OSError
   ```

---

## Implementation Plan

### Strategy

1. **Wrap all file operations** in try-except blocks
2. **Catch specific exceptions**: `PermissionError`, `OSError`, `FileExistsError`
3. **Clean up temp files** on error (best effort)
4. **Return error in result dict** instead of crashing
5. **Continue processing** other files in batch
6. **Provide helpful error messages** to user

### Error Handling Pattern

```python
try:
    # File operation (copy, move, remove)
except (PermissionError, OSError) as e:
    # Clean up temp file (best effort)
    try:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    except:
        pass  # Ignore cleanup errors

    # Return error result
    return {
        "id": id,
        "filename": os.path.abspath(original_file),
        "original_size": original_size,
        "message": f"ERROR: {descriptive_message} - {str(e)}",
    }
```

### Specific Code Changes

#### Change 1: Directory Creation (After line 398)

**Location:** After determining `output_file` path

**Add:**
```python
# Ensure the output directory exists
output_dir = os.path.dirname(output_file)
if output_dir and not os.path.exists(output_dir):
    try:
        os.makedirs(output_dir, exist_ok=True)
    except (PermissionError, OSError) as e:
        # Cannot create output directory
        try:
            os.remove(temp_file)
        except:
            pass
        return {
            "id": id,
            "filename": os.path.abspath(original_file),
            "original_size": original_size,
            "message": f"ERROR: Cannot create directory '{output_dir}' - {str(e)}",
        }
```

#### Change 2: Copy Original File (Line 414)

**Current code:**
```python
case ("original", False):  # copy the original file in the output directory
    shutil.copy(original_file, output_file)
    os.remove(temp_file)
```

**Replace with:**
```python
case ("original", False):  # copy the original file in the output directory
    try:
        shutil.copy(original_file, output_file)
    except (PermissionError, OSError) as e:
        # Failed to copy - clean up and report error
        try:
            os.remove(temp_file)
        except:
            pass
        return {
            "id": id,
            "filename": os.path.abspath(original_file),
            "original_size": original_size,
            "message": f"ERROR: Cannot write to '{output_file}' - {str(e)}",
        }

    # Only remove temp file if copy succeeded
    try:
        os.remove(temp_file)
    except:
        pass  # Best effort cleanup
```

#### Change 3: Overwrite Original (Line 419)

**Current code:**
```python
case ("new", True):  # the original file need to be overwritten
    if force:
        shutil.move(temp_file, output_file)
    else:
        # ... confirmation logic
```

**Replace with:**
```python
case ("new", True):  # the original file need to be overwritten
    if force:
        try:
            shutil.move(temp_file, output_file)
        except (PermissionError, OSError) as e:
            # File might be open/locked - report error
            try:
                os.remove(temp_file)
            except:
                pass
            return {
                "id": id,
                "filename": os.path.abspath(original_file),
                "original_size": original_size,
                "message": f"ERROR: File locked or not writable - {str(e)}",
            }
    else:
        # ... existing confirmation logic
```

#### Change 4: Move New File (Line 428)

**Current code:**
```python
case ("new", False):  # move the new file to the output directory
    shutil.move(temp_file, output_file)
```

**Replace with:**
```python
case ("new", False):  # move the new file to the output directory
    try:
        shutil.move(temp_file, output_file)
    except (PermissionError, OSError) as e:
        # Failed to move - clean up and report error
        try:
            os.remove(temp_file)
        except:
            pass
        return {
            "id": id,
            "filename": os.path.abspath(original_file),
            "original_size": original_size,
            "message": f"ERROR: Cannot write to '{output_file}' - {str(e)}",
        }
```

#### Change 5: Temp File Cleanup (Lines 407, 415, 420, 429)

**Current code:**
```python
os.remove(temp_file)
```

**Replace all with:**
```python
try:
    os.remove(temp_file)
except (PermissionError, OSError):
    # Best effort cleanup - don't fail if temp file stuck
    pass
```

---

## Error Messages

### User-Facing Error Messages

Clear, actionable messages in the output table:

| Scenario | Message |
|----------|---------|
| File locked | `ERROR: File locked or not writable - [Errno 13] Permission denied` |
| Directory not writable | `ERROR: Cannot write to 'output/file.pdf' - [Errno 13] Permission denied` |
| Directory creation failed | `ERROR: Cannot create directory 'output/nested/path' - [Errno 13] Permission denied` |
| Disk full | `ERROR: Cannot write to 'output.pdf' - [Errno 28] No space left on device` |
| Invalid path | `ERROR: Cannot create directory 'bad/path' - [Errno 2] No such file or directory` |

### Example Output

**Before (crash):**
```
Processing 3 file(s):
  0) file1.pdf
  1) file2.pdf  [LOCKED BY VIEWER]
  2) file3.pdf

Traceback (most recent call last):
  ...
PermissionError: [Errno 13] Permission denied: 'file2.pdf'
```

**After (graceful):**
```
Processing 3 file(s):
  0) file1.pdf
  1) file2.pdf
  2) file3.pdf

 # | Original   | New        | Ratio | Keeping | Filename
 0 |   1,234 KB |    876 KB  |  71%  | new     | file1.pdf
 1 |   2,345 KB |    ERROR: File locked or not writable - [Errno 13] Permission denied | file2.pdf
 2 |   3,456 KB |  2,100 KB  |  61%  | new     | file3.pdf

Processed 2 of 3 files successfully.
```

---

## Testing Strategy

### Manual Testing

1. **Test: File Locked by Another Process**
   ```bash
   # Terminal 1: Open file in PDF viewer
   # Terminal 2:
   gs_batch test.pdf --force --prefix=out_
   # Expected: ERROR message, not crash
   ```

2. **Test: Read-Only Output Directory**
   ```bash
   mkdir output_dir
   chmod 555 output_dir
   gs_batch test.pdf --prefix=output_dir/
   # Expected: ERROR message about permissions
   ```

3. **Test: Invalid Output Path**
   ```bash
   gs_batch test.pdf --prefix=/root/forbidden/
   # Expected: ERROR message about directory creation
   ```

4. **Test: Disk Full** (harder to simulate)
   ```bash
   # Create small filesystem, fill it
   # Expected: ERROR message about no space
   ```

### Automated Testing

Add to `tests/test_gsb.py`:

```python
import os
import tempfile
from unittest.mock import patch, MagicMock

def test_file_locked_error(setup_test_files):
    """Test graceful handling when output file is locked."""
    # Mock shutil.move to raise PermissionError
    with patch('shutil.move', side_effect=PermissionError("[Errno 13] Permission denied")):
        result = runner.invoke(
            cli,
            ["tests/assets/originals/file_1.pdf", "--force"]
        )

        # Should not crash
        assert result.exit_code == 0
        # Should show error message
        assert "ERROR" in result.output
        assert "locked" in result.output.lower() or "permission" in result.output.lower()

def test_output_directory_not_writable(setup_test_files, tmp_path):
    """Test graceful handling when output directory is read-only."""
    # Create read-only directory
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o555)

    result = runner.invoke(
        cli,
        ["tests/assets/originals/file_1.pdf", f"--prefix={readonly_dir}/"]
    )

    # Should not crash
    assert result.exit_code == 0
    # Should show error message
    assert "ERROR" in result.output

    # Cleanup
    readonly_dir.chmod(0o755)

def test_directory_creation_fails(setup_test_files):
    """Test graceful handling when directory creation fails."""
    with patch('os.makedirs', side_effect=PermissionError("Cannot create")):
        result = runner.invoke(
            cli,
            ["tests/assets/originals/file_1.pdf", "--prefix=nested/path/"]
        )

        assert result.exit_code == 0
        assert "ERROR" in result.output
        assert "Cannot create directory" in result.output
```

### Integration Testing

Test with real scenarios:
1. Process batch with one locked file
2. Process to read-only mount point
3. Process with insufficient disk space (if possible)
4. Process with network drive disconnected mid-operation

---

## Expected Behavior

### Before Implementation

**Strengths:**
- Fast processing when everything works

**Weaknesses:**
- Crashes on first locked file
- Entire batch fails if one file has issues
- No cleanup of temp files on error
- Stack traces shown to users
- No way to continue processing after error

### After Implementation

**Improvements:**
- ✅ No crashes from file system errors
- ✅ Batch processing continues after errors
- ✅ Temp files cleaned up properly
- ✅ Clear, actionable error messages
- ✅ Professional error handling
- ✅ Summary shows successful vs failed files

**Trade-offs:**
- Slightly more code complexity
- Small performance overhead (negligible)

---

## Benefits

### 1. Robustness
- No crashes from common real-world scenarios
- Handles Windows file locking properly
- Graceful degradation

### 2. User Experience
- Clear error messages instead of stack traces
- Batch processing doesn't fail completely
- Users understand what went wrong and why

### 3. Data Safety
- Temp files always cleaned up
- Original files never corrupted
- Failed operations don't leave artifacts

### 4. Professional Quality
- Handles edge cases gracefully
- Production-ready error handling
- Predictable behavior

### 5. Debugging
- Error messages include system error codes
- Easy to diagnose permission issues
- Clear indication of which file failed

---

## Edge Cases Considered

### Race Conditions
- File becomes locked between check and write
- File deleted between check and operation
- Directory permissions change mid-operation

**Solution:** Try-except around actual operations, not just pre-checks

### Partial Failures
- Temp file written but cannot be moved
- Directory created but file cannot be written

**Solution:** Best-effort cleanup, clear error reporting

### Platform Differences
- Windows: File locks more aggressive
- Linux: Permission model different
- macOS: Special .DS_Store files

**Solution:** Generic exception handling covers all platforms

---

## Implementation Checklist

- [ ] Add directory creation error handling (line ~399)
- [ ] Add error handling to copy operation (line 414)
- [ ] Add error handling to overwrite operation (line 419)
- [ ] Add error handling to move operation (line 428)
- [ ] Update all temp file cleanup to be try-except
- [ ] Add automated tests (3 test cases)
- [ ] Manual testing (4 scenarios)
- [ ] Update documentation if needed
- [ ] Consider adding to CHANGELOG

---

## Estimated Changes

- **File Modified:** `gs_batch/gs_batch.py`
- **Function Modified:** `move_output()` (lines 348-445)
- **Lines Added:** ~50-60 lines (error handling blocks)
- **Lines Modified:** ~5 lines (wrapping existing code)
- **Test Coverage:** +3 test cases in `tests/test_gsb.py`
- **Risk Level:** Low (only adding error handling, no logic changes)
- **Testing Time:** ~30 minutes manual + automated
- **Implementation Time:** ~1 hour

---

## Questions for Review

1. **Error Message Format:** Are the proposed error messages clear enough?
2. **Cleanup Strategy:** Is best-effort cleanup acceptable, or should we be more aggressive?
3. **Exit Code:** Should the program exit with error code if any files fail?
4. **Summary Report:** Should we add a final summary of successes vs failures?
5. **Retry Logic:** Should we attempt retries for certain errors (e.g., disk full)?
6. **Logging:** Should errors be logged to a file in addition to console output?

---

**Awaiting user approval to proceed with implementation.**
