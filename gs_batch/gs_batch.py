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
from showinfm import show_in_file_manager, stock_file_manager
import time


@click.command(no_args_is_help=True)
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
@click.argument("files", nargs=-1, type=click.Path(exists=True))
def gs_batch(
    options: str,
    prefix: str,
    suffix: str,
    compress: str,
    pdfa: int,
    files: Tuple[str],
    keep_smaller: bool,
    force: bool,
    open_path: bool,
    filter: str,
    verbose: bool,
) -> None:
    """CLI tool to batch process PDFs with Ghostscript for compression or PDF/A conversion."""

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

    # filter input files
    files = [
        f
        for f in files
        if os.path.splitext(f)[1].replace(".", "").lower() in filter.split(",")
    ]

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
    return  int(
            p.stdout.split(" ")[-1].replace(".", "")
        )

def run_ghostscript(id: int, verbose: bool, args: list) -> None:
    """Run the Ghostscript command and track progress using tqdm."""
    gs_command = get_ghostscript_command()
    full_command = [gs_command] + args
    
    if verbose:
        click.echo(f"Running command: {' '.join(full_command)}")

    # Get total page count from the file (last argument in args)
    try:
        result = subprocess.run(
                [gs_command, "-dPDFINFO", "-dBATCH", "-dNODISPLAY", args[-1]],
                capture_output=True,
                text=True,
            )
        total_length = get_total_page_count(result)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error executing Ghostscript: {e}")
        return
    except ValueError as e:
        click.secho(f'ValueError: {e}', fg='red')
        click.secho(f'Cannot determine total number of pages. Possibly "{args[-1]}" is broken? (e.g. size 0kB)', fg='red')
        return
    except Exception as e:
        click.secho(f'Unexpected error: {e}', fg='red')
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
        return
    
    # return a status value if the gs command was successful
    return True 
    

def process_file(file_info: list[int, str, list, list, str, str, bool, bool, bool]) -> Dict[str, str]:
    """Process a single PDF file with Ghostscript and move/rename the output based on size."""
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
    status: bool,
    temp_file: str,
    original_file: str,
    prefix: str,
    suffix: str,
    keep_smaller: bool,
    force: bool,
    id: int,
) -> Dict[str, str]:
    
    # Get sizes of original and temporary files
    original_size = os.path.getsize(original_file)
    
    # check if the file was successfully created
    if status:    
        """Rename or move the output file, keeping either the original or new file based on size comparison."""
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
