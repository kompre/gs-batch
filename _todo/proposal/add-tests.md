# Task: Add More Tests Covering Edge Cases

**Original Objective:** Add more tests covering edge cases

**Status:** Proposal - Awaiting User Approval

---

## Analysis

### Current Test Coverage
The existing test suite (`tests/test_gsb.py`) covers:
1. ✓ Aborting when user denies overwrite permission
2. ✓ Default copy behavior with prefix
3. ✓ Force overwrite behavior
4. ✓ Keeping original when smaller
5. ✓ Keeping new when larger (with PDF/A conversion)

### Identified Edge Cases (Not Currently Tested)

#### File Handling Edge Cases
1. **Empty input** - No files provided to CLI
2. **No matching files** - Files provided but filtered out by `--filter`
3. **Non-existent file paths** - Invalid file arguments
4. **Zero-byte PDF files** - Corrupted/empty PDFs
5. **Non-PDF files** - When filter allows other extensions
6. **Directory inputs** - What happens if user passes a directory?
7. **Symlinks** - Following or breaking symlinks
8. **Very large files** - Memory/performance edge cases
9. **Unicode filenames** - Special characters in paths

#### Option Combination Edge Cases
10. **Conflicting options** - Both `--compress` and extensive `--options`
11. **All PDF/A versions** - Currently only PDF/A-1 tested
12. **Multiple filters** - `--filter=pdf,png`
13. **Suffix without prefix** - Naming behavior
14. **Both prefix and suffix** - Combined naming
15. **Prefix as absolute path** - vs relative path behavior
16. **Empty prefix/suffix strings** - Edge behavior

#### Concurrency Edge Cases
17. **Single file processing** - Pool with 1 file
18. **Many files** - Stress test with 20+ files
19. **Keyboard interrupt handling** - Graceful shutdown (hard to test)

#### Output Path Edge Cases
20. **Output directory doesn't exist** - Should create
21. **Output directory not writable** - Permission error
22. **Output file exists** - Without `--force` flag
23. **Output filename collision** - Multiple inputs same basename
24. **Path traversal in prefix** - e.g., `--prefix=../../`

#### Ghostscript Failure Edge Cases
25. **GS not installed** - Command not found
26. **GS command fails** - Bad options or corrupt input
27. **GS produces larger file** - `keep_smaller` logic
28. **GS produces zero-byte output** - Failure handling

#### Size Comparison Edge Cases
29. **Exact same size** - Original == New
30. **New file marginally larger** - Ratio close to 1.0
31. **Compression makes file much larger** - Unexpected ratio

## Implementation Plan

### Priority 1: Critical Edge Cases (Must Have)
These could cause crashes or data loss:

**Test 1: `test_no_files_provided`**
- Run CLI with no file arguments
- Expect: Help message, no crash

**Test 2: `test_no_matching_files_filter`**
- Provide PDF files with `--filter=png`
- Expect: Graceful message, no processing

**Test 3: `test_zero_byte_pdf`**
- Create 0-byte file with .pdf extension
- Expect: Error handling, clear message, no crash

**Test 4: `test_corrupt_pdf_file`**
- Use malformed PDF (e.g., text file with .pdf extension)
- Expect: GS error caught, file marked "NOT PROCESSED"

**Test 5: `test_output_directory_creation`**
- Use prefix with non-existent nested dirs: `--prefix=a/b/c/out_`
- Expect: Directories created automatically

**Test 6: `test_output_file_exists_no_force`**
- Process same file twice without `--force`
- Expect: Error or skip, original preserved

**Test 7: `test_keep_smaller_equal_sizes`**
- Mock scenario where new_size == original_size
- Expect: Consistent behavior (keep original)

### Priority 2: Important Edge Cases (Should Have)
Improve robustness:

**Test 8: `test_unicode_filename`**
- File with unicode: `测试_file.pdf`, `café_document.pdf`
- Expect: Proper handling

**Test 9: `test_multiple_filters`**
- `--filter=pdf,png` with mixed files
- Expect: Both extensions processed

**Test 10: `test_all_pdfa_versions`**
- Test `--pdfa=1`, `--pdfa=2`, `--pdfa=3`
- Expect: All versions work

**Test 11: `test_prefix_and_suffix_combined`**
- `--prefix=out_ --suffix=_compressed`
- Expect: Correct output naming

**Test 12: `test_compression_levels`**
- Test all: `/screen`, `/ebook`, `/printer`, `/prepress`, `/default`
- Expect: Different file sizes

**Test 13: `test_single_file_processing`**
- Process exactly 1 file
- Expect: Pool handles single item

**Test 14: `test_many_files_processing`**
- Process 10+ files (create copies of test files)
- Expect: All processed successfully

### Priority 3: Nice to Have
Additional coverage:

**Test 15: `test_absolute_path_prefix`**
- Use absolute path in prefix
- Expect: Output in specified absolute location

**Test 16: `test_relative_path_behavior`**
- Run from different working directory
- Expect: Paths resolved correctly

**Test 17: `test_verbose_output`**
- Run with `--verbose` flag
- Expect: Command echoed to output

**Test 18: `test_keep_new_flag`**
- Use `--keep_new` instead of default `--keep_smaller`
- Expect: Always keeps processed file

## Test Structure Improvements

### Additional Fixtures Needed
```python
@pytest.fixture
def zero_byte_pdf(setup_test_files):
    """Create a zero-byte PDF file."""

@pytest.fixture
def corrupt_pdf(setup_test_files):
    """Create a corrupted/invalid PDF file."""

@pytest.fixture
def unicode_filename_pdf(setup_test_files):
    """Create test file with unicode characters."""

@pytest.fixture
def many_test_files(setup_test_files):
    """Create 15+ test files for bulk processing."""
```

### Parametrized Tests
Use `@pytest.mark.parametrize` for:
- All compression levels
- All PDF/A versions
- Multiple filter combinations

## Estimated Changes
- **New test functions:** 15-18
- **New fixtures:** 4-5
- **Lines added:** ~400-500 lines
- **Test execution time:** +30-60 seconds

## Benefits
1. **Reliability:** Catch edge cases before users encounter them
2. **Refactoring Safety:** Confident code changes
3. **Documentation:** Tests serve as usage examples
4. **Regression Prevention:** Avoid breaking existing behavior

## Questions for Review
1. Which priority level should we target? (All of Priority 1, some of Priority 2?)
2. Should we add coverage reporting (e.g., `pytest-cov`)?
3. Are there specific edge cases from user reports we should prioritize?
4. Should we test the actual Ghostscript integration or mock it for speed?

---

**Awaiting user approval to proceed.**
