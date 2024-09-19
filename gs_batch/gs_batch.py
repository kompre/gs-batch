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
from typing import Dict, Tuple
from showinfm import show_in_file_manager
import time


def init_worker() -> None:
    """Ignore keyboard interrupts in worker processes so that only the main process handles them."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def human_readable_size(size_in_bytes: int) -> str:
    """Convert file size from bytes to a human-readable format (KB or MB)."""
    return (
        f"{size_in_bytes / 1024:,.0f} KB"
        if size_in_bytes < 1024 * 1024
        else f"{size_in_bytes / (1024 * 1024):,.2f} MB"
    )


def get_ghostscript_command() -> str:
    """Determine the appropriate Ghostscript command based on the operating system and architecture."""
    system = platform.system()

    if system == "Windows":
        arch = platform.architecture()[0]
        gs_command = "gswin64c" if arch == "64bit" else "gswin32c"
    elif system in ["Linux", "Darwin"]:
        gs_command = "gs"
    elif system == "OS/2":
        gs_command = "gso2"
    else:
        raise OSError(f"Unsupported operating system: {system}")

    # Check if Ghostscript is available on the system
    if shutil.which(gs_command) is None:
        raise FileNotFoundError(
            f"Ghostscript command '{gs_command}' not found on the system."
        )

    return gs_command


def get_total_page_count(p: subprocess.CompletedProcess) -> int:
    """Extract the total number of pages from the Ghostscript output."""
    return int(
        p.stdout.decode("utf-8", errors="ignore").split(" ")[-1].replace(".", "")
    )


def run_ghostscript(id: int, args: list) -> None:
    """Run the Ghostscript command and track progress using tqdm."""
    gs_command = get_ghostscript_command()
    full_command = [gs_command] + args

    # Get total page count from the file (last argument in args)
    try:
        total_length = get_total_page_count(
            subprocess.run(
                [gs_command, "-dPDFINFO", "-dBATCH", args[-1]], capture_output=True
            )
        )
    except subprocess.CalledProcessError as e:
        click.echo(f"Error executing Ghostscript: {e}")
        return

    
    try:
        process = subprocess.Popen(
            full_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        with tqdm(
            total=total_length,
            desc=f"{id+1}) {args[-1]}",
            position=id,
            leave=False,
            colour="green",
        ) as bar:
            for line in iter(process.stdout.readline, b""):
                line = line.decode("utf-8", errors="ignore")
                if line.startswith("Page "):
                    bar.update(1)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error executing Ghostscript: {e}")


def process_file(file_info: Tuple[str, list, str, str, bool]) -> Dict[str, str]:
    """Process a single PDF file with Ghostscript and move/rename the output based on size."""
    id, pdf_file, command_parts, prefix, suffix, keep_smaller = file_info

    # Create a temporary output file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_output:
        temp_output_file = tmp_output.name

    # Build the Ghostscript command
    gs_command = ["-sDEVICE=pdfwrite", "-o", temp_output_file]
    gs_command.extend(command_parts)
    gs_command.append(pdf_file)

    # Run the Ghostscript command
    run_ghostscript(id, gs_command)

    # Move or rename the output file
    result = move_output(temp_output_file, pdf_file, prefix, suffix, keep_smaller)

    return result


def move_output(
    temp_file: str, original_file: str, prefix: str, suffix: str, keep_smaller: bool
) -> Dict[str, str]:
    """Rename or move the output file, keeping either the original or new file based on size comparison."""
    root, _ = os.path.split(original_file)
    input_basename, input_ext = os.path.splitext(os.path.basename(original_file))

    # Form the full output file path with prefix and suffix
    output_file = os.path.join(root, f"{prefix}{input_basename}{suffix}{input_ext}")

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # Get sizes of original and temporary files
    original_size = os.path.getsize(original_file)
    new_size = os.path.getsize(temp_file)
    ratio = new_size / original_size
    keeping = "original" if keep_smaller and new_size >= original_size else "new"

    if keeping == "original":
        os.remove(temp_file)
        shutil.move(original_file, output_file)
    else:
        shutil.move(temp_file, output_file)

    # Return result for summary
    return {
        "original_size": original_size,
        "new_size": new_size,
        "ratio": ratio,
        "keeping": keeping,
        "filename": os.path.abspath(output_file),
    }


@click.command(no_args_is_help=True)
@click.option(
    "--options", default=None, help="Arbitrary Ghostscript options and switches."
)
@click.option(
    "--compress",
    default=None,
    is_flag=False,
    flag_value="/ebook",
    help="Compression quality level (e.g., /screen, /ebook, /printer, /prepress).",
)
@click.option(
    "--pdfa",
    is_flag=False,
    flag_value=2,
    default=None,
    help="PDF/A version (e.g., 1 for PDF/A-1, 2 for PDF/A-2, 3 for PDF/A-3).",
)
@click.option("--prefix", default="", help="Prefix to add to the output file name.")
@click.option(
    "--suffix",
    default="",
    help="Suffix to add to the output file name before the extension.",
)
@click.option(
    "--keep_smaller/--keep_new",
    default=True,
    help="Keep the smaller file between old and new (default: keep smaller).",
)
@click.argument("files", nargs=-1, type=click.Path(exists=True))
def gs_batch(
    options: str,
    prefix: str,
    suffix: str,
    compress: str,
    pdfa: int,
    files: Tuple[str],
    keep_smaller: bool,
) -> None:
    """CLI tool to batch process PDFs with Ghostscript for compression or PDF/A conversion."""

    # Command building logic
    command_parts = []
    if compress:
        command_parts.append(f"-dPDFSETTINGS={compress}")
    if pdfa:
        command_parts.extend(
            [
                "-dPDFACompatibilityPolicy=1",
                "-sColorConversionStrategy=RGB",
                f"-dPDFA={pdfa}",
            ]
        )
        keep_smaller = False
    if options:
        command_parts.append(options)

    click.secho(f"Processing {len(files)} file(s)", bg="red")

    # Prepare file processing tasks
    file_tasks = [
        (id, pdf_file, command_parts, prefix, suffix, keep_smaller) for id, pdf_file in enumerate(files)
    ]

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
        f"\n{'Original':^{column_width}} | {'New':^{column_width}} | {'Ratio':^{column_width}} | {'Keeping':^{column_width}} | Filename",
        bold=True,
    )
    for r in results:
        click.echo(
            f"{human_readable_size(r['original_size']):>{column_width}} | {human_readable_size(r['new_size']):>{column_width}} | {r['ratio']:{column_width}.3%} | {r['keeping']:^{column_width}} | {r['filename']}"
        )

    click.echo(f"\nTotal time: {toc - tic:.2f} seconds")

    time.sleep(0.5)
    show_in_file_manager([r["filename"] for r in results])


if __name__ == "__main__":
    runner = click.testing.CliRunner()
    result = runner.invoke(
        gs_batch,
        r'--compress=/default --prefix=/tests/ tests/asset/mat.pdf "tests/asset/[23064 - BALSAMO - Treviso - Santa Bona Nuova] Relazione sui materiali.pdf"',
    )
    print(result.output)
