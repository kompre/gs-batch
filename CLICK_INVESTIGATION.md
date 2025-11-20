# Click 8.2+ Breaking Change Investigation

## Summary
Click 8.3.0 **broke** `is_flag=False` with `flag_value` pattern, making `--compress` (without value) fail. This wasn't a deliberate design change but a **regression bug**. The pattern worked correctly in Click 8.2.1 but broke in 8.3.0 and remains broken in 8.3.1.

## Evidence

### Click 8.2.1 (Working)
```python
@click.option("--compress", is_flag=False, flag_value="/ebook", type=click.Choice([...]))
```
✅ `--compress` → `/ebook`
✅ `--compress /screen` → `/screen`

### Click 8.3.0/8.3.1 (Broken)
Same code:
❌ `--compress` → Error: "Option '--compress' requires an argument"
✅ `--compress /screen` → `/screen`

## Root Cause
- **Click ≤8.2.1**: Pattern works correctly with `is_flag=False` + `flag_value` + `type=Choice`
- **Click 8.3.0**: Reworked flag handling in this version broke the `is_flag=False` pattern entirely
- **Click 8.3.1**: Regression persists

The `is_flag=False` + `flag_value` pattern is **non-functional** in Click 8.3.0+ due to regression. No official deprecation notice exists - it simply stopped working.

## Solutions

### Option 1: Pin to Click <8.3 (Recommended)
**Pros:** No code changes, preserves existing UX, includes 8.2.x improvements
**Cons:** Misses Click 8.3+ improvements

### Option 2: Custom OptionalChoice Type
```python
class OptionalChoice(click.Choice):
    def __init__(self, choices, default_value):
        super().__init__(choices)
        self.default_value = default_value

    def convert(self, value, param, ctx):
        return self.default_value if value == "" else super().convert(value, param, ctx)

@click.option("--compress", type=OptionalChoice([...], "/ebook"))
```
**UX:** Requires `--compress=` (with equals) for default
**Pros:** Works with Click 8.3+, proper validation
**Cons:** Different syntax than before

### Option 3: Separate Flag + Option
```python
@click.option("--compress-level", type=click.Choice([...]))
@click.option("--compress", is_flag=True, flag_value="/ebook")
```
**Pros:** Clean Click 8.3+ solution
**Cons:** Breaking API change

## Recommendation
**Update fix to pin Click <8.3** (currently pinned to <8.2). This is a Click **regression/bug** in 8.3.0, not an official deprecation or designed breaking change. The pattern worked in 8.2.1 and should still work. Monitor Click 8.3.2+ for fixes, or file an issue to clarify Click's intent.

## Test Results
Added tests (`test_compress_flag_default_value`, `test_pdfa_flag_default_value`) to catch future regressions.

## Click Repository Status

**Click 8.3.0 Deliberate Changes:**
- **PR #3030**: Major refactoring of flag_value handling
  - Introduced `UNSET` sentinel value to distinguish "no value" from "None as value"
  - Fixed issues: #1992, #2514, #2610, #3024, #3030
  - **Side effect**: Broke `is_flag=False` + `flag_value` pattern (unintentional)

**Related Issues:**
- **#2140** (Closed 2021): "`flag_value` is ignored" - Similar symptom
- **#2897** (Open 2025): Boolean flags broken in 8.2.0
- **#2894**: Click 8.2.0 ignores `is_flag` options with type

**Root Cause Analysis:**
The 8.3.0 flag handling refactor (PR #3030) was intended to fix edge cases with `flag_value=None` and `default` interactions. However, it inadvertently broke the `is_flag=False` + `flag_value` pattern that worked in 8.2.x.

**Verdict:** This is an **unintentional regression** from the 8.3.0 refactoring. Worth reporting as:
1. Pattern worked in Click ≤8.2.1
2. Broke in Click 8.3.0 as side effect of PR #3030
3. Not mentioned in release notes or migration guide
4. Request: restore pattern OR document breaking change with migration path


## GitHub Issue Draft

**Title:** `is_flag=False` with `flag_value` stopped working in Click 8.3.0 (regression from 8.2.x)

**Description:**

The pattern `is_flag=False` with `flag_value` worked in Click 8.2.x but broke in Click 8.3.0 without announcement. This appears to be an unintentional regression rather than a designed breaking change. 

## Bug Description

Using `@click.option()` with `is_flag=False` and `flag_value` set allows an option to work both as a flag (using the flag_value) and with an explicit value. This pattern worked in Click ≤8.2.1 but fails in 8.3.0+ with "Option requires an argument" error.

## Minimal Reproduction

```python
import click

@click.command()
@click.option(
    "--compress",
    default=None,
    is_flag=False,
    flag_value="/ebook",
    type=click.Choice(["/ebook", "/screen"]),
)
def test_cmd(compress):
    click.echo(f"compress = {compress!r}")

if __name__ == "__main__":
    test_cmd()
```

**Click 8.2.1 behavior (working):**
```bash
$ python test.py --compress
compress = '/ebook'

$ python test.py --compress /screen
compress = '/screen'
```

**Click 8.3.0/8.3.1 behavior (broken):**
```bash
$ python test.py --compress
Error: Option '--compress' requires an argument.

$ python test.py --compress /screen
compress = '/screen'
```

## Expected Behavior

When using `is_flag=False` with `flag_value="/ebook"`, the option should:
1. Accept `--compress` alone and use the flag_value (`/ebook`)
2. Accept `--compress /screen` and use the provided value

This worked in Click 8.2.1 and earlier versions.

## Environment

- Python version: 3.13.3 (also tested on 3.12)
- Click versions tested:
  - 8.2.0: ✅ Works
  - 8.2.1: ✅ Works
  - 8.2.2: ⚠️ Yanked ("Unintended change in behavior")
  - 8.3.0: ❌ **BROKEN** (regression introduced)
  - 8.3.1: ❌ Still broken
- OS: Windows 11

## Related Issues and Context

**Click 8.3.0 Changes:**
This regression appears to be an unintended side effect of PR #3030, which refactored flag handling to fix:
- #1992: Binary flags vs `default=None` semantics
- #2514: Make `flag_value=None` actually work
- #2610, #3024, #3030: Other flag_value inconsistencies

The PR introduced an `UNSET` sentinel value to better handle `flag_value` and `default` interactions, but inadvertently broke the `is_flag=False` + `flag_value` pattern.

**Other Related Issues:**
- #2894 (Click 8.2.0 ignores is_flag options with type)
- #2140 (flag_value is ignored - closed)

## Question

Is this regression intentional? If so:
1. Should this pattern be officially deprecated with migration guidance?
2. What's the recommended alternative for Click 8.3+?

If unintentional, can the 8.2.x behavior be restored in 8.3.2+?

## Impact

This breaks existing CLIs that relied on this pattern, requiring either:
- Pin to Click <8.3 (loses Click 8.3+ improvements)
- Rewrite options with different UX
- Implement custom workarounds

## Regression Timeline

- Click ≤8.2.1: Pattern works correctly
- Click 8.3.0: **Regression introduced** - `is_flag=False` + `flag_value` stops working
- Click 8.3.1: Regression persists
