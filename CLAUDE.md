# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`gs-batch-pdf` is a CLI tool for batch processing PDF files using Ghostscript. It supports compression, PDF/A conversion, and custom Ghostscript operations with multi-threaded processing.

## Development Commands

The project uses `uv` for dependency management.

### Package Management
```bash
# Environment setup
uv sync                          # Install dependencies and sync environment
uv sync --dev                    # Install with development dependencies

# Testing
uv run pytest                    # Run all tests
uv run pytest tests/test_gsb.py  # Run specific test file
uv run pytest -v                 # Verbose test output

# Development
uv run python -m gs_batch.gs_batch --help  # Test CLI locally
uv run gs_batch --help           # Test installed CLI command
```

### Building and Distribution
```bash
uv build                         # Create wheel and source distributions
uv publish                       # Publish to PyPI (requires credentials)
```

## Architecture

### Core Structure
- **`gs_batch/gs_batch.py`**: Main CLI application using Click framework
- **`gs_batch/assets/`**: Contains Ghostscript configuration files:
  - `PDFA_def.ps`: PDF/A conversion definitions
  - `srgb.icc`: Color profile for PDF/A compliance

### CLI Design
- Main command: `gs_batch` (alias: `gsb`)
- Uses Click for command-line interface with extensive options
- Multi-threaded processing using Python's `multiprocessing`
- Progress tracking with `tqdm`
- File management with automatic prefix/suffix handling

### Key Features
- **Batch Processing**: Parallel PDF processing with configurable thread count
- **Compression**: Multiple quality levels (/screen, /ebook, /printer, /prepress, /default)
- **PDF/A Conversion**: Supports PDF/A-1, PDF/A-2, PDF/A-3 standards
- **Smart File Management**:
  - Keeps smaller file by default (`--keep_smaller`)
  - Configurable output naming with prefix/suffix
  - Safe overwrite protection (requires `--force` for in-place operations)

### Testing Structure
- **`tests/test_gsb.py`**: Main test suite using pytest and Click's CliRunner
- **`tests/assets/originals/`**: Sample PDF files for testing
- **`tests/assets/output/`**: Expected test outputs
- Tests cover file handling, compression, overwrite behavior, and size comparisons

## Development Patterns

### Error Handling
- Graceful handling of Ghostscript failures
- User confirmation prompts for destructive operations
- Comprehensive logging and progress feedback

### File Operations
- All file operations respect the `--keep_smaller`/`--keep_new` flags
- Temporary file management for safe processing
- Cross-platform path handling

## Dependencies

### Runtime
- `click`: CLI framework
- `tqdm`: Progress bars
- `show-in-file-manager`: Cross-platform file manager integration

### Development
- `pytest`: Testing framework
- `ipykernel`: Jupyter notebook support

### External
- **Ghostscript**: Required system dependency for PDF processing

## Task Planning and Management

### `_todo` Directory Structure
The project uses a structured planning system located in `_todo/`:

```
_todo/
├── todo.md                    # Master task list written by user
├── proposal/                  # Initial task proposals
│   └── [task-name].md        # Claude's detailed plan awaiting user approval
├── pending/                   # Active development files
│   └── [task-name].md        # Approved tasks with progress updates
└── completed/                 # Finished tasks archive
    └── YYYY-MM-DD/           # Date-based folders for completion date
        └── [task-name].md    # Final summary + insights
```

### Planning Workflow
1. **Task Creation**: User writes tasks in `_todo/todo.md` with clear objectives and priorities
2. **Proposal Phase**: Claude creates detailed proposal in `_todo/proposal/[task-name].md`
   - Include original objective from todo.md and remove it from todo.md
   - Break down into specific implementation steps
   - Wait for user review, comments, and approval
3. **Development Phase**: After user approval, move proposal to `_todo/pending/[task-name].md`
   - Update file with implementation progress and activity summaries
   - Use for ongoing development updates
4. **Completion**: After task completion, move file to `_todo/completed/YYYY-MM-DD/`
   - Update with final summary and insights
   - Mark task as "Completed" in todo.md

### Session Startup Protocol
**IMPORTANT**: At the start of each session, always check:
1. `_todo/todo.md` for new or updated tasks from the user
2. `_todo/proposal/` for user-reviewed proposals ready to approve/implement
3. `_todo/pending/` for active tasks requiring progress updates
4. Current git status and recent commits for context