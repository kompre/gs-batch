# gs-batch-pdf

A command-line tool for batch processing PDF files using [Ghostscript](https://www.ghostscript.com/) with parallel execution. Process multiple PDFs simultaneously while applying compression, PDF/A conversion, or custom Ghostscript options. 

## Features

- **Parallel Processing**: Multi-threaded execution for faster batch operations
- **Compression**: Multiple quality levels (/screen, /ebook, /printer, /prepress, /default)
- **PDF/A Conversion**: Support for PDF/A-1, PDF/A-2, and PDF/A-3 standards[^1]
- **Recursive Search**: Process entire directory trees with the `-r` flag
- **Smart File Management**: Keep smaller files automatically or always keep new versions
- **Error Handling**: Configurable error behavior (prompt, skip, or abort)
- **Custom Ghostscript Options**: Full access to Ghostscript's command-line options
- **Progress Tracking**: Real-time progress bars for each file being processed
- **Flexible Output**: Add prefixes/suffixes to output filenames, organize into folders
- **Cross-platform**: Windows, Linux, and macOS support

[^1]: Requires Ghostscript version 10.04.0 or higher for correct PDF/A-2 and PDF/A-3 conversion.

## Installation

### Prerequisites

1. **Python 3.12+**: Required to run the tool
2. **Ghostscript**: Required for PDF processing. Install from [ghostscript.com](https://www.ghostscript.com/) 

### Install gs-batch-pdf

Using [pipx](https://pipx.pypa.io/stable/) (recommended)[^2]:

```bash
pipx install gs-batch-pdf
```

Or using pip:

```bash
pip install gs-batch-pdf
```

[^2]: pipx installs the package in an isolated virtual environment while making commands globally available.


## Usage

The tool is available via two commands: `gs_batch` or its shorter alias `gsb`.

### Basic Syntax

```bash
gsb [OPTIONS] FILES_OR_DIRECTORIES...
```

or (my preference):

```bash
gsb FILES_OR_DIRECTORIES... [OPTIONS]
```

### Quick Start

```bash
# Compress all PDFs in current directory (default: /ebook quality)
gsb . --compress

# Compress PDFs recursively in a directory tree
gsb ./docs/ -r --compress

# Convert a single PDF to PDF/A-2
gsb file.pdf --pdfa

# Compress and convert to PDF/A with custom output
gsb *.pdf --compress --pdfa --prefix "processed_"
```

> **Note**: When using options that can take optional values (like `--compress` or `--pdfa`), place them **after** the file arguments for simplest usage, or see [Using Options with File Arguments](#using-options-with-file-arguments) for alternatives.

### Options

#### Processing Options

- `--compress [LEVEL]`: Compress PDFs with quality level
  - Levels: `/screen`, `/ebook` (default), `/printer`, `/prepress`, `/default`
  - Use without value for `/ebook` quality

- `--pdfa [VERSION]`: Convert to PDF/A format
  - Versions: `1` (PDF/A-1), `2` (PDF/A-2, default), `3` (PDF/A-3)
  - Use without value for PDF/A-2

- `--options TEXT`: Pass arbitrary Ghostscript options
  - Example: `--options "-dColorImageResolution=100 -dCompatibilityLevel=1.4"`

#### File Management Options

- `--prefix TEXT`: Add prefix to output filenames
  - Can include path: `--prefix "output/"` creates files in output directory
  - Relative paths calculated from input file location, not current directory

- `--suffix TEXT`: Add suffix before file extension
  - Example: `--suffix "_compressed"` → `file_compressed.pdf`

- `--keep_smaller` / `--keep_new`: Choose which file to keep (default: `--keep_smaller`)
  - `--keep_smaller`: Keep whichever file is smaller (original or processed)
  - `--keep_new`: Always keep the processed file
  - Note: PDF/A conversion always keeps new file

- `-f, --force`: Allow overwriting original files without confirmation
  - Required when no prefix specified and files would be overwritten

#### Search Options

- `--filter TEXT`: Filter files by extension (default: `pdf`)
  - Supports comma-separated list: `--filter pdf,png`

- `-r, --recursive`: Search directories recursively
  - Without this flag, only processes files in top-level directories

#### Error Handling Options

- `--on-error [MODE]`: Control behavior when file processing errors occur
  - `prompt` (default): Interactively ask user whether to retry, skip, or abort
  - `skip`: Automatically skip failed files and continue processing
  - `abort`: Stop processing immediately on first error

#### Other Options

- `--timeout INTEGER`: Maximum processing time per file in seconds (default: 300)
  - Set to `0` to disable timeout protection
  - Prevents indefinite hangs on problematic PDFs
- `--open_path` / `--no_open_path`: Open output location in file manager (default: enabled)
- `-v, --verbose`: Show detailed Ghostscript command output
- `--version`: Show version information
- `--help`: Display help message

### Using Options with File Arguments

When using options that accept optional values (`--compress`, `--pdfa`), you have three approaches:

**1. Place options after file arguments (recommended):**
```bash
gsb *.pdf --compress
gsb * --compress --pdfa
```

**2. Provide explicit values:**
```bash
gsb --compress /ebook *.pdf
gsb --pdfa 2 *.pdf
```

**3. Use `--` separator:**
```bash
gsb --compress -- *.pdf
gsb --pdfa -- *.pdf
```

## Examples

### Basic Compression

Compress multiple PDFs with /ebook quality (in-place)[^3]:

```bash
gsb file1.pdf file2.pdf file3.pdf --compress
```

Compress all PDFs in a directory:

```bash
gsb . --compress
```

Compress with specific quality level:

```bash
gsb document.pdf --compress /screen
# or with explicit value before files:
gsb --compress /screen *.pdf
```

[^3]: When no `--prefix` is provided and files would be overwritten, you'll be prompted for confirmation unless `--force` is used.

### PDF/A Conversion

Convert to PDF/A-2 (default):

```bash
gsb report.pdf --pdfa
```

Convert to specific PDF/A version:

```bash
gsb document.pdf --pdfa 3
# or with explicit value before files:
gsb --pdfa 3 *.pdf
```

Compress and convert to PDF/A:

```bash
gsb invoice.pdf --compress --pdfa
```

### Recursive Processing

Process entire directory tree:

```bash
# Find and compress all PDFs in current directory and subdirectories
gsb . -r --compress

# Process specific directory recursively
gsb ./documents/ -r --compress --pdfa
```

Process with force (no confirmation):

```bash
gsb . -r --compress --pdfa --force
```

### Custom Output Organization

Add prefix to create organized output:

```bash
# Add prefix to filenames
gsb *.pdf --prefix "compressed_" --compress

# Create files in subdirectory
gsb *.pdf --prefix "output/" --compress

# Add both prefix and suffix
gsb *.pdf --prefix "processed_" --suffix "_v1" --compress
```

Keep new files regardless of size:

```bash
gsb document.pdf --compress --keep_new
```

### Advanced Ghostscript Options

Apply custom Ghostscript settings:

```bash
gsb file.pdf --options "-dCompatibilityLevel=1.4 -dColorImageResolution=72"
```

Combine compression with custom options:

```bash
gsb report.pdf --compress /printer --options "-dCompatibilityLevel=1.7"
```

### Error Handling

Interactive error handling (default):

```bash
# Prompts user on each error to retry, skip, or abort
gsb . -r --compress
```

Skip failed files automatically:

```bash
# Useful for batch processing where some files may be corrupted
gsb . -r --compress --on-error skip
```

Abort on first error:

```bash
# Stops immediately if any file fails (useful for CI/CD)
gsb *.pdf --compress --on-error abort
```

### Scripting and Automation

Silent processing for scripts:

```bash
gsb *.pdf --compress --force --no_open_path
```

Automated batch with error skipping:

```bash
# Best for unattended processing
gsb . -r --compress --force --no_open_path --on-error skip
```

Verbose output for debugging:

```bash
gsb document.pdf -v --compress --pdfa
```

Process with custom timeout for large files:

```bash
# Set 10 minute timeout for very large PDFs
gsb large-document.pdf --compress --timeout 600

# Disable timeout for files that take a long time
gsb complex-document.pdf --compress --timeout 0
```

## Output

After processing completes, gs-batch-pdf displays a detailed summary table:

```
Processing 3 file(s):
  1) document1.pdf
  2) document2.pdf
  3) document3.pdf

[Progress bars shown during processing...]

  # |  Original  |    New     |   Ratio    |  Keeping   | Filename
  1 |   1,234 KB |    856 KB  |   69.400%  |    new     | /path/to/document1.pdf
  2 |     789 KB |    654 KB  |   82.900%  |    new     | /path/to/document2.pdf
  3 |     456 KB |    512 KB  |  112.300%  |  original  | /path/to/document3.pdf

Total time: 12.34 seconds
```

The summary shows:
- **Original**: Size of the input file
- **New**: Size of the processed file
- **Ratio**: New size as percentage of original (lower is better for compression)
- **Keeping**: Which version was kept based on `--keep_smaller` or `--keep_new`
- **Filename**: Absolute path to the output file

By default, the tool opens the output location in your file manager after processing (disable with `--no_open_path`).

## Troubleshooting

### Ghostscript Not Found

If you get an error about Ghostscript not being found:

1. Verify Ghostscript is installed: `gs --version` (Linux/macOS) or `gswin64c --version` (Windows)
2. Ensure Ghostscript is in your system PATH
3. On Windows, you may need to restart your terminal after installation

### PDF/A Conversion Issues

For PDF/A-2 and PDF/A-3 conversion, ensure you're using Ghostscript 10.04.0 or higher:

```bash
gs --version
```

### Permission Errors

If you encounter permission errors when processing files:

- Use `--prefix` to write to a different directory
- Check file permissions on both input and output locations
- On Windows, ensure files aren't open in another program

### Timeout Issues

If processing is hanging or taking too long:

- The default timeout is 5 minutes (300 seconds) per file
- For large or complex PDFs, increase the timeout: `--timeout 600` (10 minutes)
- To disable timeout protection: `--timeout 0`
- Some corrupted PDFs may cause Ghostscript to hang indefinitely - timeout protection will terminate these processes

## Contributing

Contributions are welcome! Please feel free to:

- Report bugs or request features via [GitHub Issues](https://github.com/kompre/gs-batch/issues)
- Submit Pull Requests for improvements
- Share feedback and suggestions

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

This tool is built on top of [Ghostscript](https://www.ghostscript.com/), released under the GNU Affero General Public License (AGPL). gs-batch-pdf is a CLI wrapper and is independently licensed under MIT.