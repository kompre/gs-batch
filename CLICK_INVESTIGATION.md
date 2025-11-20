# Click 8.2+ Breaking Change Investigation

## Summary
Click 8.2.0+ **broke** `is_flag=False` with `flag_value` pattern, making `--compress` (without value) fail. This wasn't a deliberate design change but a **regression bug** that was partially fixed in 8.2.1/8.2.2 but still broken in 8.3.1.

## Evidence

### Click 8.1.8 (Working)
```python
@click.option("--compress", is_flag=False, flag_value="/ebook")
```
✅ `--compress` → `/ebook`
✅ `--compress /screen` → `/screen`

### Click 8.3.1 (Broken)
Same code:
❌ `--compress` → Error: "Option '--compress' requires an argument"
✅ `--compress /screen` → `/screen`

## Root Cause
- **Click 8.2.0**: Regression where `is_flag=False` with `type` parameter broke flag_value handling ([Issue #2894](https://github.com/pallets/click/issues/2894))
- **Click 8.2.1**: Partial fix for flags with type
- **Click 8.2.2**: Fixed reconciliation of `default`, `flag_value`, and `type`
- **Click 8.3.0**: Reworked flag handling broke `is_flag=False` pattern entirely

The `is_flag=False` + `flag_value` pattern is now **deprecated/broken** in Click 8.2+.

## Solutions

### Option 1: Pin to Click <8.2 (Current)
**Pros:** No code changes, preserves existing UX
**Cons:** Misses Click 8.2+ improvements/fixes

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
**Keep current fix** (Pin to <8.2). This is a Click regression, not a designed breaking change. The `is_flag=False` pattern should work but doesn't. Monitor Click 8.4+ for fixes to this regression.

## Test Results
Added tests (`test_compress_flag_default_value`, `test_pdfa_flag_default_value`) to catch future regressions.
