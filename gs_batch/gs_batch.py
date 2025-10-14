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
) -> None:
    """CLI wrapper for gs_batch_impl - see help parameter in @click.command decorator."""
    return _gs_batch_impl(
        options, prefix, suffix, compress, pdfa, files,
        keep_smaller, force, open_path, filter, verbose, recursive
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
        (id, pdf_file, command_parts, first_argument, prefix, suffix, keep_smaller, force, verbose)
        for id, pdf_file in enumerate(files)
    ]

    for file in file_tasks:
        click.echo(
            f"{file[0]:>{2+id_width}d}) {file[1]}"
        )  # right align the id and indent b y 2 spaces

    tic = time.time()
    try:
        with multiprocessing.Pool(initializer=init_worker) as pool:
            results = pool.map(process_file, file_tasks)
    except KeyboardInterrupt:
        click.echo("\nProcess interrupted. Terminating pool...")
        pool.terminate()
        pool.join()
        sys.exit(1)
    toc = time.time()

    # Print summary table
    column_width = 10

    click.secho(
        f"\n {'#':>{id_width}s} | {'Original':^{column_width}} | {'New':^{column_width}} | {'Ratio':^{column_width}} | {'Keeping':^{column_width}} | Filename",
        bold=True,
    )
    
    for r in results:
        if r.get("message"):
            click.secho(
                f" {r['id']:>{id_width}d} | {human_readable_size(r['original_size']):>{column_width}} |    {r['message']:^{3*column_width}}    | {r['filename']}",
                fg="red",
            )
        else:
            click.echo(
                f" {r['id']:>{id_width}d} | {human_readable_size(r['original_size']):>{column_width}} | {human_readable_size(r['new_size']):>{column_width}} | {r['ratio']:{column_width}.3%} | {r['keeping']:^{column_width}} | {r['filename']}"
            )

    click.echo(f"\nTotal time: {toc - tic:.2f} seconds")

    # open files folder and select them
    if open_path:
        time.sleep(0.5)
        show_in_file_manager(
            [r["filename"] for r in results]
            if stock_file_manager() != "nautilus"
            else results[0]["filename"]
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
        # Try both 'gs' and 'ghostscript' (snap installs as 'ghostscript')
        gs_command = "gs"
        if shutil.which(gs_command) is None:
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

def run_ghostscript(id: int, verbose: bool, args: List[str]) -> Optional[bool]:
    """Run Ghostscript command with progress tracking.

    Executes Ghostscript on a PDF file while displaying a progress bar that
    tracks page processing. The function first determines the total page count,
    then runs the main Ghostscript command and updates progress as each page
    is processed.

    Args:
        id: Task identifier for progress bar positioning in multiprocessing.
        verbose: If True, prints the full Ghostscript command before execution.
        args: Ghostscript command arguments including output file and input PDF.
              The last argument must be the input PDF path.

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

        with tqdm(
            total=total_length,
            desc=f"{id+1}) {args[-1]}",
            position=id,
            leave=False,
            colour="green",
        ) as bar:
            for line_bytes in iter(process.stdout.readline, b""):
                line = line_bytes.decode("utf-8", errors="ignore")
                if line.startswith("Page "):
                    bar.update(1)

    except subprocess.CalledProcessError as e:
        click.echo(f"Error executing Ghostscript: {e}")
        return None

    # return a status value if the gs command was successful
    return True 
    

def process_file(file_info: Tuple[int, str, List[str], List[str], str, str, bool, bool, bool]) -> Dict[str, Any]:
    """Process a single PDF file with Ghostscript.

    Processes a PDF file using Ghostscript with specified compression or PDF/A
    conversion settings, then moves/renames the output based on size comparison.

    Args:
        file_info: Tuple containing (id, pdf_file, command_parts, first_argument,
                   prefix, suffix, keep_smaller, force, verbose) where:
                   - id: Task identifier for progress tracking
                   - pdf_file: Path to input PDF file
                   - command_parts: Ghostscript command arguments
                   - first_argument: Additional command prefix arguments
                   - prefix: Output filename prefix
                   - suffix: Output filename suffix
                   - keep_smaller: If True, keep smaller file; if False, keep new file
                   - force: If True, allow overwriting original files
                   - verbose: If True, show detailed command output

    Returns:
        Dictionary containing processing results with keys:
        - 'id': Task identifier
        - 'filename': Absolute path to output file
        - 'original_size': Size of original file in bytes
        - 'new_size': Size of processed file in bytes (if successful)
        - 'ratio': Compression ratio as float (if successful)
        - 'keeping': "original" or "new" indicating which file was kept
        - 'message': Error message (if processing failed)

    Example:
        >>> task = (0, "input.pdf", ["-dPDFSETTINGS=/screen"], [], "", "_compressed", True, False, False)
        >>> result = process_file(task)
        >>> print(result['keeping'])
        new
    """
    id, pdf_file, command_parts, first_argument, prefix, suffix, keep_smaller, force, verbose = file_info

    # Create a temporary output file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_output:
        temp_output_file = tmp_output.name

    # Build the Ghostscript command
    gs_command = ["-sDEVICE=pdfwrite", "-o", temp_output_file]
    gs_command.extend(command_parts)
    gs_command.extend(first_argument)
    gs_command.append(pdf_file)

    # Run the Ghostscript command
    status = run_ghostscript(id, verbose, gs_command)

    # Move or rename the output file

    result = move_output(
        status, temp_output_file, pdf_file, prefix, suffix, keep_smaller, force, id
    )


    return result


def move_output(
    status: Optional[bool],
    temp_file: str,
    original_file: str,
    prefix: str,
    suffix: str,
    keep_smaller: bool,
    force: bool,
    id: int,
) -> Dict[str, Any]:
    """Move or rename processed PDF based on size comparison.

    Handles output file placement after Ghostscript processing, deciding whether
    to keep the original or processed file based on size comparison and user
    preferences. Manages file overwrites and directory creation.

    Args:
        status: Ghostscript execution result (True=success, None=failure).
        temp_file: Path to temporary processed PDF file.
        original_file: Path to original input PDF file.
        prefix: Prefix to add to output filename (can include directory path).
        suffix: Suffix to add to output filename before extension.
        keep_smaller: If True, keep whichever file is smaller; if False, always keep processed file.
        force: If True, allow overwriting files without prompt.
        id: Task identifier for result tracking.

    Returns:
        Dictionary with processing results:
        - If successful: 'id', 'filename', 'original_size', 'new_size', 'ratio', 'keeping'
        - If failed: 'id', 'filename', 'original_size', 'message'

    Example:
        >>> result = move_output(True, "/tmp/output.pdf", "input.pdf", "compressed_", "", True, False, 0)
        >>> print(result['keeping'])
        new
    """

    # Get sizes of original and temporary files
    original_size = os.path.getsize(original_file)

    # check if the file was successfully created
    if status:
        root, _ = os.path.split(original_file)
        input_basename, input_ext = os.path.splitext(os.path.basename(original_file))

        # Form the full output file path with prefix and suffix
        output_file = os.path.join(root, f"{prefix}{input_basename}{suffix}{input_ext}")

        # Ensure the output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        
        new_size = os.path.getsize(temp_file)
        ratio = new_size / original_size

        # conditions for file copy or move
        keeping = "original" if keep_smaller and new_size >= original_size else "new"
        is_same_path = os.path.abspath(original_file) == os.path.abspath(output_file)

        match (keeping, is_same_path):
            case ("original", True):  # no action is needed
                os.remove(temp_file)

            case ("original", False):  # copy the original file in the output directory
                shutil.copy(original_file, output_file)
                os.remove(temp_file)

            case ("new", True):  # the original file need to be overwritten
                if force:
                    shutil.move(temp_file, output_file)
                else:
                    click.echo(
                        f"Error: {output_file} already exists. Use the `--force` flag to allow overwriting files and skip this messages."
                    )
                    keeping = "original"
                    os.remove(temp_file)

            case ("new", False):  # move the new file to the output directory
                shutil.move(temp_file, output_file)

        # Return result for summary
        return {
            "original_size": original_size,
            "new_size": new_size,
            "ratio": ratio,
            "keeping": keeping,
            "filename": os.path.abspath(output_file),
            "id": id,
        }
    else:
        return {
            "id": id,
            "filename": os.path.abspath(original_file),
            "original_size": original_size,
            "message": "FILE NOT PROCESSED!",
        }

from importlib.resources import files, as_file
from pathlib import Path

def get_asset_path(asset_name: str) -> str:
    """Get the path to an asset file."""
    path = str(files('gs_batch.assets').joinpath(asset_name)).replace('\\', '/')
    return path

if __name__ == "__main__":
    gs_batch()
