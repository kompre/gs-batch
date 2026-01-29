# Click 8.3.0 Compatibility Fix

## Issue
After updating dependencies with `uv lock --upgrade`, Click was upgraded from 8.1.7 → 8.3.1, which broke the `--compress` and `--pdfa` flags. They stopped accepting flag-only usage (e.g., `--compress` without a value) and started requiring explicit arguments.

## Root Cause
Click 8.3.0 PR #3030 introduced an `UNSET` sentinel to better distinguish between "no default" and "`default=None`". This changed how `default=None` interacts with `flag_value` in the `is_flag=False` pattern.

**Breaking combination:** `default=None` + `is_flag=False` + `flag_value`
- Click ≤8.2.1: ✅ Works
- Click 8.3.0+: ❌ Broken - "Option requires an argument"

## Solution
Remove the explicit `default=None` parameter while keeping `is_flag=False` and `flag_value`. This allows Click to use its internal `UNSET` sentinel, which works correctly across all versions.

**Before:**
```python
@click.option(
    "--compress",
    default=None,           # ❌ This breaks in Click 8.3.0+
    is_flag=False,
    flag_value="/ebook",
    type=click.Choice(["/screen", "/ebook", "/printer", "/prepress", "/default"]),
)
```

**After:**
```python
@click.option(
    "--compress",
    is_flag=False,          # ✅ Works in all Click versions
    flag_value="/ebook",
    type=click.Choice(["/screen", "/ebook", "/printer", "/prepress", "/default"]),
)
```

## Additional Fix: Click 8.3.0 Abort Handling
Click 8.3.0 changed how `click.prompt()` handles aborts (Ctrl+C or empty input). Previously it was handled gracefully by the application, but now it prints "Aborted!" and exits with code 1.

**Solution:** Wrap prompts in `try/except click.Abort`:
```python
try:
    response = click.prompt("Continue?", type=click.Choice(["y", "n"]), default="n")
    # handle response
except click.Abort:
    click.echo("Aborting...")
    return  # Exit gracefully with code 0
```

## Changes Made

### gs_batch/gs_batch.py
1. Removed `default=None` from `--compress` and `--pdfa` options
2. Restored `type=click.Choice()` validation (removed manual validation workaround)
3. Added `try/except click.Abort` around both `click.prompt()` calls

### pyproject.toml
- Updated Click dependency: `click>=8.1.7,<8.2` → `click>=8.1.7` (no upper bound)

### Test Results
✅ All 22 tests pass with Click 8.3.1
- Tested with Click 8.1.7, 8.1.8, 8.2.1, 8.3.0, and 8.3.1 - all working
- No breaking changes to CLI UX

## References
- Click PR #3030: Flag handling refactor that introduced the regression
- Click 8.3.0 release: https://click.palletsprojects.com/en/stable/changes/#version-8-3-0
