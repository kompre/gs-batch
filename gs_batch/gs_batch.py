import click
import subprocess
import os
import tempfile
import platform
import shutil
import multiprocessing
import click.testing
from tqdm import tqdm
import signal
import sys
from typing import Dict, Tuple, List, Optional, Any, Union
from showinfm import show_in_file_manager, stock_file_manager
import time
from importlib.metadata import version, PackageNotFoundError


def get_version() -> str:
    """Get package version from metadata."""
    try:
        return version("gs-batch-pdf")
    except PackageNotFoundError:
        return "unknown"


def get_package_info() -> str:
    """Get formatted package information for epilogue display."""
    from importlib.metadata import metadata
    try:
        meta = metadata("gs-batch-pdf")
        pkg_version = meta.get("Version", "unknown")
        author = meta.get("Author", "kompre")
        return f"gs-batch-pdf v{pkg_version} | by {author} | https://github.com/kompre/gs-batch"
    except PackageNotFoundError:
        return "gs-batch-pdf | https://github.com/kompre/gs-batch"


def get_epilog() -> str:
    """Get formatted epilog with examples and package info."""
    return f"""Examples: gsb --compress . | gsb -r --compress ./docs/ | gsb --pdfa file.pdf

{get_package_info()}"""


@click.command(
    no_args_is_help=True,
    epilog=get_epilog(),
    help="Batch process PDF files using Ghostscript with parallel compression and format conversion."
)
@click.version_option(version=get_version(), prog_name="gs-batch-pdf")
@click.option(
    "--options",
    default=None,
    help="Arbitrary Ghostscript options and switches. (e.g. '-dColorImageResolution=100 -dCompatibilityLevel=1.4').",
)
@click.option(
    "--compress",
    default=None,
    is_flag=False,
    flag_value="/ebook",
    show_default=True,
    type=click.Choice(["/screen", "/ebook", "/printer", "/prepress", "/default"]),
    help="Compression quality level (e.g., /screen, [/ebook], /printer, /prepress, /default).",
)
@click.option(
    "--pdfa",
    is_flag=False,
    flag_value="2",
    default=None,
    type=click.Choice(["1", "2", "3"]),
    help="PDF/A version (e.g., 1 for PDF/A-1, 2 for [PDF/A-2], 3 for PDF/A-3).",
)
@click.option(
    "--prefix",
    default="",
    help="Prefix to add to the output file name. Can be path-like (e.g., 'pdfs/'). NOTE: relative path are calculated relative to input pdf file position, not the current working directory.",
)
@click.option(
    "--suffix",
    default="",
    help="Suffix to add to the output file name before the extension.",
)
@click.option(
    "--keep_smaller/--keep_new",
    default=True,
    show_default=True,
    help="Keep the smaller file between old and new.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Allow overwriting the original file.",
)
@click.option(
    "--open_path/--no_open_path",
    default=True,
    help="Open the output file path in the filesystem.",
)
@click.option(
    "--filter",
    default="pdf",
    show_default=True,
    help="Filter input files by extension; could be comma-separated. (e.g., 'pdf,png')",
)
@click.option(
    "--verbose","-v",
    is_flag=True,
    default=False,
    help="Show verbose output.",
)
@click.option(
    "--recursive", "-r",
    is_flag=True,
    default=False,
    help="Recursively search directories for files matching --filter extension(s).",
)
@click.option(
    "--on-error",
    default="prompt",
    type=click.Choice(["prompt", "skip", "abort"]),
    show_default=True,
    help="Action on file errors: [prompt] user interactively, skip failed files and continue, or abort on first error.",
)
@click.option(
    "--timeout",
    default=300,
    type=int,
    show_default=True,
    help="Maximum processing time per file in seconds (0 = no timeout).",
)
@click.argument("files", nargs=-1, type=str)
def gs_batch(
    options: str,
    prefix: str,
    suffix: str,
    compress: str,
    pdfa: int,
    files: Union[Tuple[str, ...], List[str]],
    keep_smaller: bool,
    force: bool,
    open_path: bool,
    filter: str,
    verbose: bool,
    recursive: bool,
    on_error: str,
    timeout: int,
) -> None:
    """CLI wrapper for gs_batch_impl - see help parameter in @click.command decorator."""
    return _gs_batch_impl(
        options, prefix, suffix, compress, pdfa, files,
        keep_smaller, force, open_path, filter, verbose, recursive, on_error, timeout
    )


def _gs_batch_impl(
    options: str,
    prefix: str,
    suffix: str,
    compress: str,
    pdfa: int,
    files: Union[Tuple[str, ...], List[str]],
    keep_smaller: bool,
    force: bool,
    open_path: bool,
    filter: str,
    verbose: bool,
    recursive: bool,
    on_error: str,
    timeout: int,
) -> None:
    """Batch process PDF files with Ghostscript for compression or PDF/A conversion.

    A command-line tool that processes multiple PDF files in parallel using
    Ghostscript. Supports compression, PDF/A conversion, and custom Ghostscript
    options. Processes files using multiprocessing for improved performance and
    displays progress bars for each file.

    Args:
        options: Arbitrary Ghostscript options and switches as a string.
                 Example: '-dColorImageResolution=100 -dCompatibilityLevel=1.4'
        prefix: Prefix to add to output filename. Can include directory path.
                Relative paths are calculated from input file location, not CWD.
        suffix: Suffix to add to output filename before the extension.
        compress: Compression quality level. One of: /screen, /ebook, /printer,
                  /prepress, /default. Default /ebook if flag used without value.
        pdfa: PDF/A version for conversion. One of: 1 (PDF/A-1), 2 (PDF/A-2),
              3 (PDF/A-3). Default 2 if flag used without value.
        files: Tuple of file or directory paths to process.
        keep_smaller: If True, keep smaller file between original and processed.
                      If False, always keep the processed file. Overridden to
                      False when using PDF/A conversion.
        force: If True, allow overwriting original files without confirmation.
               Otherwise, prompts user if no prefix is specified.
        open_path: If True, open output location in file manager after processing.
        filter: Comma-separated file extensions to include. Default: "pdf".
                Example: "pdf,png" to process both PDFs and PNGs.
        verbose: If True, display detailed command output and progress information.
        recursive: If True, recursively search directories for files matching filter.
                   If False, only process files in the top level of directories.
        on_error: Action to take on file errors. One of:
                  - 'prompt': Interactively prompt user (default, existing behavior)
                  - 'skip': Skip failed files and continue processing
                  - 'abort': Stop processing on first error
        timeout: Maximum processing time per file in seconds. Use 0 for no timeout.
                 Default: 300 seconds (5 minutes).

    Returns:
        None. Prints summary table and processing results to stdout.

    Side Effects:
        - Creates/overwrites files in filesystem
        - May prompt user for overwrite confirmation
        - Opens file manager if open_path=True
        - Exits with code 1 if invalid paths provided
        - Prints progress bars and summary to stdout

    Example:
        >>> # Compress all PDFs in current directory
        >>> gs_batch(None, "compressed_", "", "/ebook", None, tuple(["./"]),
        ...          True, False, False, "pdf", False, True)

        >>> # Convert to PDF/A-2 with custom prefix
        >>> gs_batch(None, "archive/", "_pdfa", None, "2", tuple(["input.pdf"]),
        ...          False, True, True, "pdf", True, False)
    """

    # Check that Ghostscript is available and functional
    check_ghostscript_available()

    # Validate that paths exist
    invalid_paths = [f for f in files if not os.path.exists(f)]
    if invalid_paths:
        for path in invalid_paths:
            click.secho(f"Error: Path does not exist: {path}", fg="red", err=True)
        sys.exit(1)

    # Parse filter extensions
    filter_extensions = [ext.lower() for ext in filter.split(",")]
    original_count = len(files)

    # Find files (with optional recursion)
    files = find_files_recursive(files, filter_extensions, recursive)

    # Early exit if no files match
    if not files:
        click.secho("No files found matching the specified filter.", fg="yellow", err=True)
        click.echo(f"Filter: {filter}", err=True)
        if verbose:
            click.echo(f"Searched {original_count} path(s), found 0 matching files.", err=True)
        return

    # overwriting alert
    if not prefix and not force:
        if on_error == "abort":
            click.secho("Error: No --prefix specified and --force not set", fg="red", err=True)
            click.secho("Use --prefix to specify output location or --force to allow overwriting", err=True)
            sys.exit(1)
        elif on_error == "skip":
            click.secho("Warning: No --prefix specified and --force not set", fg="yellow", err=True)
            click.secho("Skipping all files (use --force to allow overwriting or --prefix for output location)", fg="yellow", err=True)
            return
        else:  # prompt
            click.secho("**WARNINGS:**", bold=True, blink=True, bg="red", nl=False)
            click.secho(
                " Original files may be overwritten if no `--prefix` is specified",
                bold=True,
                fg="red",
            )
            click.secho(
                "(Use the `--force` flag to allow overwriting original files and skip this messages)",
                fg="black",
            )
            response = click.prompt(
                "Do you want to overwrite original files?",
                default="n",
                type=click.Choice(["y", "n"]),
            )
            if response == "y":
                force = True
            else:
                click.echo("Aborting...")
                return

    # Command building logic
    command_parts = []
    first_argument = []
    if compress:
        command_parts.append(f"-dPDFSETTINGS={compress}")
    if pdfa:
        command_parts.extend(
            [
                "-dPDFACompatibilityPolicy=1",
                "-sColorConversionStrategy=RGB",
                f"-dPDFA={pdfa}",
                f"--permit-file-read={get_asset_path('srgb.icc')}",
            ]
        )
        first_argument = [
            '-c',
            f"/ICCProfile ({get_asset_path('srgb.icc')}) def" ,
            "-f",
            get_asset_path("PDFA_def.ps"),
        ]
        keep_smaller = False
    if options:
        command_parts.extend(options.split())

    # print input files
    id_width = len(
        str(len(files))
    )  # determine the width of the id column as number of digit in len(files)

    click.secho(f"Processing {len(files)} file(s):", bg="red")

    # Prepare file processing tasks
    file_tasks = [
        (id, pdf_file, command_parts, first_argument, prefix, suffix, keep_smaller, force, verbose, on_error, timeout)
        for id, pdf_file in enumerate(files)
    ]

    for file in file_tasks:
        click.echo(
            f"{file[0]:>{2+id_width}d}) {file[1]}"
        )  # right align the id and indent b y 2 spaces

    tic = time.time()
    try:
        with multiprocessing.Pool(initializer=init_worker) as pool:
            gs_results = pool.map(process_file, file_tasks)
    except KeyboardInterrupt:
        click.echo("\nProcess interrupted. Terminating pool...")
        pool.terminate()
        pool.join()
        sys.exit(1)

    # Process file operations serially in main thread
    final_results = []
    try:
        for gs_result in gs_results:
            if gs_result['status'] == 'success':
                final_result = finalize_output(gs_result)
                final_results.append(final_result)
            else:
                # GS failed - return error result
                final_results.append(create_error_result(gs_result, "Ghostscript processing failed"))
    except AbortBatchProcessing as e:
        click.secho(f"\nBatch processing aborted by user: {e}", fg="red")
        sys.exit(1)

    toc = time.time()

    # Print summary table
    column_width = 10

    click.secho(
        f"\n {'#':>{id_width}s} | {'Original':^{column_width}} | {'New':^{column_width}} | {'Ratio':^{column_width}} | {'Keeping':^{column_width}} | Filename",
        bold=True,
    )

    for r in final_results:
        if r.get("message"):
            click.secho(
                f" {r['id']:>{id_width}d} | {human_readable_size(r['original_size']):>{column_width}} |    {r['message']:^{3*column_width}}    | {r['filename']}",
                fg="red",
            )
        else:
            click.echo(
                f" {r['id']:>{id_width}d} | {human_readable_size(r['original_size']):>{column_width}} | {human_readable_size(r['new_size']):>{column_width}} | {r['ratio']:{column_width}.3%} | {r['keeping']:^{column_width}} | {r['filename']}"
            )

    # Summary statistics
    total_files = len(final_results)
    successful_files = sum(1 for r in final_results if 'message' not in r)
    failed_files = total_files - successful_files

    # Calculate total sizes for successfully processed files only
    total_original_size = sum(r['original_size'] for r in final_results if 'message' not in r)
    total_new_size = sum(r['new_size'] for r in final_results if 'message' not in r)
    total_ratio = total_new_size / total_original_size if total_original_size > 0 else 0.0

    if failed_files > 0:
        click.secho(
            f"\nProcessed {successful_files} of {total_files} files successfully. "
            f"{failed_files} file(s) failed.",
            fg="yellow" if successful_files > 0 else "red"
        )
    else:
        click.secho(f"\nAll {total_files} file(s) processed successfully.", fg="green")

    # Display size statistics for successfully processed files
    if successful_files > 0:
        click.echo(
            f"Total: {human_readable_size(total_original_size)} → "
            f"{human_readable_size(total_new_size)} ({total_ratio:.1%})"
        )

    click.echo(f"Total time: {toc - tic:.2f} seconds")

    # open files folder and select them
    if open_path:
        time.sleep(0.5)
        show_in_file_manager(
            [r["filename"] for r in final_results]
            if stock_file_manager() != "nautilus"
            else final_results[0]["filename"]
        )


def init_worker() -> None:
    """Ignore keyboard interrupts in worker processes so that only the main process handles them."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def human_readable_size(size_in_bytes: int) -> str:
    """Convert file size from bytes to a human-readable format (KB or MB)."""
    return f"{size_in_bytes / 1024:,.0f} KB"


def find_files_recursive(
    paths: Union[Tuple[str, ...], List[str]],
    filter_extensions: List[str],
    recursive: bool
) -> List[str]:
    """Find all files matching filter, optionally searching recursively.

    Args:
        paths: File or directory paths to search.
        filter_extensions: List of extensions to include (e.g., ['pdf', 'png']).
        recursive: If True, search directories recursively.

    Returns:
        List of file paths matching the filter.
    """
    found_files = []

    for path in paths:
        if os.path.isfile(path):
            # Direct file argument - include if matches filter
            ext = os.path.splitext(path)[1].replace(".", "").lower()
            if ext in filter_extensions:
                found_files.append(path)

        elif os.path.isdir(path):
            if recursive:
                # Recursive directory search (followlinks=True per user decision)
                try:
                    for root, dirs, files in os.walk(path, followlinks=True):
                        for file in files:
                            ext = os.path.splitext(file)[1].replace(".", "").lower()
                            if ext in filter_extensions:
                                found_files.append(os.path.join(root, file))
                except PermissionError:
                    # Warn about inaccessible directories per user decision
                    click.secho(f"Warning: Permission denied: {path}", fg="yellow", err=True)
            else:
                # Non-recursive: only direct children
                try:
                    for item in os.listdir(path):
                        item_path = os.path.join(path, item)
                        if os.path.isfile(item_path):
                            ext = os.path.splitext(item)[1].replace(".", "").lower()
                            if ext in filter_extensions:
                                found_files.append(item_path)
                except PermissionError:
                    click.secho(f"Warning: Permission denied: {path}", fg="yellow", err=True)
        else:
            # Path doesn't exist (shouldn't happen due to earlier validation)
            click.secho(f"Warning: Skipping invalid path: {path}", fg="yellow", err=True)

    return found_files


def get_ghostscript_command() -> str:
    """Determine the appropriate Ghostscript command based on the operating system and architecture."""
    system = platform.system()

    if system == "Windows":
        arch = platform.architecture()[0]
        gs_command = "gswin64c" if arch == "64bit" else "gswin32c"
    elif system in ["Linux", "Darwin"]:
        # Try to find gs in various locations
        # First try standard PATH
        gs_command = "gs"
        if shutil.which(gs_command) is None:
            # Try snap installation location
            snap_gs = "/snap/bin/gs"
            if os.path.exists(snap_gs):
                return snap_gs
            # Try 'ghostscript' command (some snap installations)
            gs_command = "ghostscript"
    elif system == "OS/2":
        gs_command = "gso2"
    else:
        raise OSError(f"Unsupported operating system: {system}")

    # Check if Ghostscript is available on the system
    if shutil.which(gs_command) is None:
        raise FileNotFoundError(
            f"Ghostscript command '{gs_command}' not found on the system. "
            f"Please install Ghostscript using your package manager (apt, snap, brew, etc.)."
        )

    return gs_command


def check_ghostscript_available() -> None:
    """Verify that Ghostscript is installed and functional.

    Performs two checks:
    1. Verifies the Ghostscript command exists and responds to --version
    2. Tests that Ghostscript can actually execute (not blocked by sandboxing)

    Raises:
        SystemExit: If Ghostscript is not available or not functional, with a
                   helpful error message and troubleshooting guidance.
    """
    try:
        gs_command = get_ghostscript_command()
    except (FileNotFoundError, OSError) as e:
        click.secho("Error: Ghostscript is not installed or not found in PATH", fg="red", err=True)
        click.echo(f"Details: {e}", err=True)
        click.echo("\nTroubleshooting:", err=True)
        click.echo("  - Install Ghostscript using your package manager:", err=True)
        click.echo("    • Ubuntu/Debian: sudo apt-get install ghostscript", err=True)
        click.echo("    • macOS: brew install ghostscript", err=True)
        click.echo("    • Windows: Download from https://www.ghostscript.com/", err=True)
        click.echo("  - Ensure Ghostscript is in your PATH", err=True)
        sys.exit(1)

    # Check 1: Verify command exists and responds to --version
    try:
        result = subprocess.run(
            [gs_command, "--version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            click.secho("Error: Ghostscript command exists but failed to run", fg="red", err=True)
            stderr_text = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
            if stderr_text:
                click.echo(f"Error output: {stderr_text}", err=True)
            sys.exit(1)
    except subprocess.TimeoutExpired:
        click.secho("Error: Ghostscript command timed out", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Error: Failed to run Ghostscript: {e}", fg="red", err=True)
        sys.exit(1)

    # Check 2: Test that Ghostscript can actually execute (catches sandboxing issues)
    try:
        result = subprocess.run(
            [gs_command, "-sDEVICE=nullpage", "-dBATCH", "-dNODISPLAY", "-c", "quit"],
            capture_output=True,
            timeout=5
        )
        if result.returncode != 0:
            click.secho("Error: Ghostscript is installed but cannot execute properly", fg="red", err=True)
            stderr_text = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
            if stderr_text:
                click.echo(f"Error output: {stderr_text}", err=True)

            # Check if this might be a snap sandboxing issue
            if "snap" in gs_command or "/snap/" in gs_command:
                click.echo("\nThis appears to be a snap installation of Ghostscript.", err=True)
                click.echo("Snap packages may have sandboxing restrictions that prevent file access.", err=True)
                click.echo("\nRecommended solution:", err=True)
                click.echo("  1. Remove snap version: sudo snap remove ghostscript", err=True)
                click.echo("  2. Install via apt: sudo apt-get install ghostscript", err=True)
            sys.exit(1)
    except subprocess.TimeoutExpired:
        click.secho("Error: Ghostscript test execution timed out", fg="red", err=True)
        sys.exit(1)
    except Exception as e:
        click.secho(f"Error: Failed to test Ghostscript execution: {e}", fg="red", err=True)
        sys.exit(1)


def get_total_page_count(p: subprocess.CompletedProcess) -> int:
    """Extract the total number of pages from Ghostscript PDF info output.

    Parses the last token from Ghostscript's -dPDFINFO output which contains
    the page count.

    Args:
        p: Completed subprocess result from Ghostscript with -dPDFINFO flag.

    Returns:
        Total number of pages in the PDF file.

    Raises:
        ValueError: If the output cannot be parsed as an integer.

    Example:
        >>> result = subprocess.run(["gs", "-dPDFINFO", "-dBATCH", "-dNODISPLAY", "file.pdf"],
        ...                         capture_output=True, text=True)
        >>> pages = get_total_page_count(result)
        >>> print(pages)
        10
    """
    return int(
        p.stdout.split(" ")[-1].replace(".", "")
    )

def run_ghostscript(id: int, verbose: bool, args: List[str], timeout: float = 300) -> Optional[bool]:
    """Run Ghostscript command with progress tracking and timeout protection.

    Executes Ghostscript on a PDF file while displaying a progress bar that
    tracks page processing. The function first determines the total page count,
    then runs the main Ghostscript command and updates progress as each page
    is processed. Includes timeout protection to prevent indefinite hangs.

    Args:
        id: Task identifier for progress bar positioning in multiprocessing.
        verbose: If True, prints the full Ghostscript command before execution.
        args: Ghostscript command arguments including output file and input PDF.
              The last argument must be the input PDF path.
        timeout: Maximum execution time in seconds (default: 300 = 5 minutes).

    Returns:
        True if Ghostscript executed successfully, None if an error occurred.

    Raises:
        subprocess.CalledProcessError: If Ghostscript command fails.
        ValueError: If PDF page count cannot be determined.

    Example:
        >>> args = ["-sDEVICE=pdfwrite", "-o", "output.pdf", "input.pdf"]
        >>> success = run_ghostscript(0, True, args)
        >>> if success:
        ...     print("Processing completed")
    """
    gs_command = get_ghostscript_command()
    full_command = [gs_command] + args

    if verbose:
        click.echo(f"Running command: {' '.join(full_command)}")

    # Get total page count from the file (last argument in args)
    try:
        result = subprocess.run(
                [gs_command, "-dPDFINFO", "-dBATCH", "-dNODISPLAY", args[-1]],
                capture_output=True,
            )

        # Check if Ghostscript command succeeded
        if result.returncode != 0:
            stderr_text = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
            click.secho(f'Ghostscript failed to get PDF info (exit code {result.returncode})', fg='red')
            if verbose and stderr_text:
                click.echo(f"Ghostscript stderr: {stderr_text}", err=True)
            return None

        # Decode output with error handling for non-UTF-8 characters
        try:
            stdout_text = result.stdout.decode('utf-8')
        except UnicodeDecodeError:
            # Try common alternative encodings
            try:
                stdout_text = result.stdout.decode('latin-1')
            except UnicodeDecodeError:
                stdout_text = result.stdout.decode('utf-8', errors='replace')

        # Create a compatible result object with decoded text
        # Using a simple object to hold stdout as string for get_total_page_count
        from types import SimpleNamespace
        decoded_result = SimpleNamespace(
            stdout=stdout_text,
            stderr=result.stderr.decode('utf-8', errors='replace') if result.stderr else '',
            returncode=result.returncode
        )
        total_length = get_total_page_count(decoded_result)  # type: ignore[arg-type]

        # Log stderr if present and verbose
        if verbose and decoded_result.stderr:
            click.echo(f"Ghostscript stderr: {decoded_result.stderr}", err=True)

    except subprocess.CalledProcessError as e:
        click.echo(f"Error executing Ghostscript: {e}")
        if verbose and e.stderr:
            click.echo(f"Stderr: {e.stderr}", err=True)
        return None
    except ValueError as e:
        click.secho(f'ValueError: {e}', fg='red')
        click.secho(f'Cannot determine total number of pages. Possibly "{args[-1]}" is broken? (e.g. size 0kB)', fg='red')
        return None
    except UnicodeDecodeError as e:
        click.secho(f'UnicodeDecodeError: {e}', fg='red')
        click.secho(f'Cannot decode Ghostscript output. This may be a locale/encoding issue.', fg='red')
        return None
    except Exception as e:
        click.secho(f'Unexpected error: {e}', fg='red')
        return None


    try:
        process = subprocess.Popen(
            full_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        if process.stdout is None:
            click.echo("Error: Failed to capture Ghostscript output")
            return None

        start_time = time.time()
        last_progress_time = start_time

        with tqdm(
            total=total_length,
            desc=f"{id+1}) {args[-1]}",
            position=id,
            leave=False,
            colour="green",
        ) as bar:
            while True:
                # Check for timeout
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    click.secho(f'\nGhostscript timeout ({timeout}s) - terminating process', fg='red')
                    process.kill()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                    return None

                # Read line with timeout using select/poll on Unix or short timeout on Windows
                try:
                    line_bytes = process.stdout.readline()
                    if not line_bytes:
                        # EOF reached
                        break

                    line = line_bytes.decode("utf-8", errors="ignore")
                    if line.startswith("Page "):
                        bar.update(1)
                        last_progress_time = time.time()

                except Exception as e:
                    click.secho(f'Error reading Ghostscript output: {e}', fg='red')
                    process.kill()
                    return None

        # Wait for process to complete with timeout
        try:
            returncode = process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            click.secho(f'Ghostscript failed to terminate cleanly - killing process', fg='red')
            process.kill()
            process.wait()
            return None

        if returncode != 0:
            click.secho(f'Ghostscript processing failed (exit code {returncode})', fg='red')
            if verbose:
                click.echo(f"Command: {' '.join(full_command)}", err=True)
            return None

    except subprocess.CalledProcessError as e:
        click.echo(f"Error executing Ghostscript: {e}")
        return None
    except Exception as e:
        click.secho(f'Unexpected error during Ghostscript execution: {e}', fg='red')
        return None

    # return a status value if the gs command was successful
    return True 
    

def process_file(file_info: Tuple[int, str, List[str], List[str], str, str, bool, bool, bool, str, int]) -> Dict[str, Any]:
    """Process a single PDF file with Ghostscript.

    Processes a PDF file using Ghostscript with specified compression or PDF/A
    conversion settings. Returns temp file path and metadata for later finalization.

    Args:
        file_info: Tuple containing (id, pdf_file, command_parts, first_argument,
                   prefix, suffix, keep_smaller, force, verbose, on_error, timeout) where:
                   - id: Task identifier for progress tracking
                   - pdf_file: Path to input PDF file
                   - command_parts: Ghostscript command arguments
                   - first_argument: Additional command prefix arguments
                   - prefix: Output filename prefix
                   - suffix: Output filename suffix
                   - keep_smaller: If True, keep smaller file; if False, keep new file
                   - force: If True, allow overwriting original files
                   - verbose: If True, show detailed command output
                   - on_error: Action on file errors ('prompt', 'skip', or 'abort')
                   - timeout: Maximum processing time in seconds (0 = no timeout)

    Returns:
        Dictionary containing processing results with keys:
        - 'id': Task identifier
        - 'status': 'success' or 'gs_failed'
        - 'original_file': Path to original input file
        - 'original_size': Size of original file in bytes
        - 'temp_file': Path to Ghostscript output (if successful)
        - 'new_size': Size of processed file in bytes (if successful)
        - 'prefix': Output filename prefix
        - 'suffix': Output filename suffix
        - 'keep_smaller': Whether to keep smaller file
        - 'force': Whether to force overwrite
        - 'on_error': Action on file errors

    Example:
        >>> task = (0, "input.pdf", ["-dPDFSETTINGS=/screen"], [], "", "_compressed", True, False, False, "prompt", 300)
        >>> result = process_file(task)
        >>> print(result['status'])
        success
    """
    id, pdf_file, command_parts, first_argument, prefix, suffix, keep_smaller, force, verbose, on_error, timeout = file_info

    original_size = os.path.getsize(pdf_file)

    # Create a temporary output file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_output:
        temp_output_file = tmp_output.name

    # Build the Ghostscript command
    gs_command = ["-sDEVICE=pdfwrite", "-o", temp_output_file]
    gs_command.extend(command_parts)
    gs_command.extend(first_argument)
    gs_command.append(pdf_file)

    # Run the Ghostscript command with timeout (0 = infinite)
    actual_timeout = timeout if timeout > 0 else float('inf')
    status = run_ghostscript(id, verbose, gs_command, actual_timeout)

    # Return temp file info for finalization in main thread
    if status:
        new_size = os.path.getsize(temp_output_file)
        return {
            'id': id,
            'status': 'success',
            'original_file': pdf_file,
            'original_size': original_size,
            'temp_file': temp_output_file,
            'new_size': new_size,
            'prefix': prefix,
            'suffix': suffix,
            'keep_smaller': keep_smaller,
            'force': force,
            'on_error': on_error,
        }
    else:
        # GS failed - cleanup temp file
        try:
            if os.path.exists(temp_output_file):
                os.remove(temp_output_file)
        except:
            pass

        return {
            'id': id,
            'status': 'gs_failed',
            'original_file': pdf_file,
            'original_size': original_size,
            'prefix': prefix,
            'suffix': suffix,
            'keep_smaller': keep_smaller,
            'force': force,
            'on_error': on_error,
        }


# Error handling helpers
class AbortBatchProcessing(Exception):
    """Exception raised when user chooses to abort batch processing."""
    pass


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


def prompt_retry_skip_abort(filename: str, error: Exception, on_error: str) -> str:
    """
    Prompt user for action on recoverable error, or auto-respond based on on_error mode.

    Args:
        filename: Name of file being processed
        error: The exception that occurred
        on_error: Action mode ('prompt', 'skip', or 'abort')

    Returns: 'retry' | 'skip' | 'abort'
    """
    if on_error == "skip":
        click.secho(f"\nError processing '{os.path.basename(filename)}': {error}", fg="yellow")
        click.echo("  Skipping file (--on-error skip)")
        return "skip"
    elif on_error == "abort":
        click.secho(f"\nError processing '{os.path.basename(filename)}': {error}", fg="red")
        click.echo("  Aborting batch (--on-error abort)")
        return "abort"
    else:  # prompt
        click.secho(f"\nError processing '{os.path.basename(filename)}':", fg="yellow")
        click.echo(f"  {error}")

        suggestion = get_error_suggestion(error)
        if suggestion:
            click.echo(f"  Suggestion: {suggestion}")

        # Display options with explanations
        click.echo("\nAvailable actions:")
        click.echo("  [r]etry  - Try the operation again (after fixing the issue)")
        click.echo("  [s]kip   - Skip this file and continue with the next one")
        click.echo("  [a]bort  - Stop processing all files and exit")

        response = click.prompt(
            "\nChoose action",
            type=click.Choice(['r', 's', 'a'], case_sensitive=False),
            default='r',
            show_default=True
        )

        action_map = {'r': 'retry', 's': 'skip', 'a': 'abort'}
        return action_map[response.lower()]


def retry_file_operation(operation, filename: str, op_type: str, on_error: str) -> None:
    """
    Execute file operation with unlimited retry on recoverable errors.

    Args:
        operation: Callable that performs the file operation
        filename: Filename for error messages
        op_type: Type of operation for error messages ('copy', 'move', 'overwrite')
        on_error: Action mode ('prompt', 'skip', or 'abort')

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
                action = prompt_retry_skip_abort(filename, e, on_error)

                if action == 'retry':
                    continue  # Loop to retry
                elif action == 'skip':
                    raise Exception(f"Skipped by user: {e}")
                else:  # abort
                    raise AbortBatchProcessing(f"User aborted on {op_type} error: {e}")
            else:
                # Non-recoverable error
                raise Exception(f"Cannot {op_type} file '{filename}': {e}")


def finalize_output(gs_result: Dict[str, Any]) -> Dict[str, Any]:
    """Move processed file from temp location to final destination.

    Handles file locking with user prompts for retry/skip/abort.
    Runs in main thread to enable user interaction.

    Args:
        gs_result: Result dict from worker containing temp file path and metadata

    Returns:
        Final result dict for output table
    """
    id = gs_result['id']
    original_file = gs_result['original_file']
    original_size = gs_result['original_size']
    temp_file = gs_result['temp_file']
    new_size = gs_result['new_size']
    prefix = gs_result['prefix']
    suffix = gs_result['suffix']
    keep_smaller = gs_result['keep_smaller']
    force = gs_result['force']
    on_error = gs_result['on_error']

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
    if keep_smaller:
        # Keep smaller file (default behavior for compression)
        keeping = "new" if new_size < original_size else "original"
    else:
        # Always keep new file (e.g., for PDF/A conversion)
        keeping = "new"

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
                    "copy",
                    on_error
                )
                cleanup_temp_file(temp_file)

            case ("new", True):
                # Overwrite original with new
                if force:
                    retry_file_operation(
                        lambda: shutil.move(temp_file, output_file),
                        output_file,
                        "overwrite",
                        on_error
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
                    "move",
                    on_error
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


from importlib.resources import files, as_file
from pathlib import Path

def get_asset_path(asset_name: str) -> str:
    """Get the path to an asset file."""
    path = str(files('gs_batch.assets').joinpath(asset_name)).replace('\\', '/')
    return path

if __name__ == "__main__":
    gs_batch()
