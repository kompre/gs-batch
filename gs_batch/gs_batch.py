import click
import subprocess
import os
import tempfile
import shutil
import sys
from click.testing import CliRunner
from concurrent.futures import ProcessPoolExecutor

def human_readable_size(size_in_bytes):
    """Convert file size from bytes to a human-readable format."""
    if size_in_bytes >= 1024 * 1024:
        size = size_in_bytes / (1024 * 1024)
        return f"{size:.3f} MB"
    else:
        size = size_in_bytes / 1024
        return f"{size:.3f} KB"


def run_ghostscript(args):
    """Helper function to run the Ghostscript command."""
    try:
        subprocess.run(args, check=True)
        click.echo(f"Ghostscript command executed successfully.")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error executing Ghostscript: {e}")

def process_file(file_info):
    """Process a single file with Ghostscript."""
    pdf_file, command_parts, prefix, suffix, keep_smaller = file_info

    # Create a temporary output file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_output:
        temp_output_file = tmp_output.name

    # Base Ghostscript command
    gs_command = ["gswin64c", "-sDEVICE=pdfwrite", "-q", "-o", temp_output_file]
    gs_command.extend(command_parts)
    gs_command.append(pdf_file)

    # Execute the Ghostscript command
    result = run_ghostscript(gs_command)

    # Rename the output file
    rename_output(temp_output_file, pdf_file, prefix, suffix, keep_smaller)
    
    return result


def rename_output(temp_file, original_file, prefix, suffix, keep_smaller):
    """Rename or move the smaller file (old or new) based on the --keep_smaller flag."""
    
    # Get the base name and extension of the original file
    input_basename, input_ext = os.path.splitext(os.path.basename(original_file))
    
    # Form the full output file path with prefix and suffix
    output_file = f"{prefix}{input_basename}{suffix}{input_ext}"
    
    # Ensure the directory exists; if not, create it
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        click.echo(f"Creating directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
    
    # Get sizes of original and temporary files
    original_size = os.path.getsize(original_file)
    new_size = os.path.getsize(temp_file)
    
    column_width = 14
    
    # Print human-readable sizes
    click.echo(f"{'Original size':^{column_width}s} | {'New size':^{column_width}s} | {'Ratio':^{column_width}s} | {'keeping':^{column_width}s}") 
    # Calculate percentage difference
    ratio = (new_size / original_size) 

    # Determine which file to keep based on the --keep_smaller flag
    if keep_smaller and new_size >= original_size:
        status = "original"
        os.remove(temp_file)  # Delete the temporary file
    else:
        status = "new"
        shutil.move(temp_file, output_file)
    click.echo(f"{human_readable_size(original_size):>{column_width}s} | {human_readable_size(new_size):>{column_width}s} | {ratio:{column_width}.3%} | { status:^{column_width}s}")
    

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
    flag_value="2",
    default=None,
    help="PDF/A version (e.g., 1 for PDF/A-1, 2 for PDF/A-2).",
)
@click.option("--prefix", default="", help="Prefix to add to the output file name.")
@click.option(
    "--suffix",
    default="",
    help="Suffix to add to the output file name before the extension.",
)
@click.option(
    "--keep_smaller/--keep_new", default=True, help="Keep the smaller file between old and new (default: keep smaller)."
)
@click.argument("files", nargs=-1, type=click.Path(exists=True))
def gs_batch(options, prefix, suffix, compress, pdfa, files, keep_smaller):
    """A CLI tool to run Ghostscript batch operations with options for compressing and converting to PDF/A."""

    # We will store options in the order they were passed.
    command_parts = []

    # We detect the order by checking sys.argv and append the correct options accordingly.
    commands_to_apply = [
        command
        for arg in sys.argv
        if (command := arg.split("=")[0]) in ["--compress", "--pdfa", "--options"]
    ]
    
    ## uncomment for debugging because sys.argv is different using the invoker
    # commands_to_apply = ['--compress']
    
    for command in commands_to_apply:
        match command:
            case "--compress":
                command_parts.append(f"-dPDFSETTINGS={compress}")
            case "--pdfa":
                command_parts.append(
                    f"-dPDFACompatibilityPolicy=1 -sColorConversionStrategy=RGB -dPDFA={pdfa}"
                )
            case "--options":
                command_parts.append(options)

    click.echo(f'Files to process: {len(files)}', color='red')
    
     # Prepare file processing tasks
    file_tasks = [(pdf_file, command_parts, prefix, suffix, keep_smaller) for pdf_file in files]

    # Process files in parallel using ProcessPoolExecutor
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(process_file, file_tasks))

    # Print results
    for result in results:
        click.echo(result)
    
    # for pdf_file in files:
    #     # Create a temporary output file
    #     with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_output:
    #         temp_output_file = tmp_output.name

    #     # Base Ghostscript command
    #     gs_command = ["gswin64c", "-sDEVICE=pdfwrite", "-q", "-o", temp_output_file]

    #     # Add the Ghostscript options based on the order captured
    #     for part in command_parts:
    #         gs_command.extend(part.split())
        
    #     # Append the input PDF file
    #     gs_command.append(pdf_file)

    #     # Execute the Ghostscript command
    #     click.echo(f"\nProcessing {pdf_file} with options: \n\n\t{' '.join(gs_command)}\n\n", color='green')
    #     run_ghostscript(gs_command)

    #     # Rename the output file, ensuring the directory for the prefix exists
    #     rename_output(temp_output_file, pdf_file, prefix, suffix, keep_smaller)


if __name__ == "__main__":
    runner = CliRunner()
    result = runner.invoke(gs_batch, r'--compress=/ebook --prefix=".\\compressed\\" mat.pdf')
    print(result.output)
