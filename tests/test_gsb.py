import os
import shutil
import tempfile
import pytest
from click.testing import CliRunner
from gs_batch.gs_batch import gs_batch as gsb
import time


# Helper function to set up temporary test files
@pytest.fixture
def setup_test_files():
    temp_dir = tempfile.mkdtemp()
    originals_dir = "tests/assets/originals"

    # Verify originals directory exists
    if not os.path.exists(originals_dir):
        raise FileNotFoundError(f"Originals directory not found: {originals_dir}")

    # Copy test files to the temp directory
    for file_name in ["file_1.pdf", "file_2.pdf", "file_3.pdf"]:
        source = os.path.join(originals_dir, file_name)
        dest = os.path.join(temp_dir, file_name)

        # Verify source file exists before copying
        if not os.path.exists(source):
            raise FileNotFoundError(f"Source test file not found: {source}")

        shutil.copy(source, dest)

        # Verify file was copied successfully
        if not os.path.exists(dest):
            raise FileNotFoundError(f"Failed to copy file to temp directory: {dest}")

        # Verify copied file has content
        if os.path.getsize(dest) == 0:
            raise ValueError(f"Copied file is empty: {dest}")

    yield temp_dir

    # Clean up after tests
    shutil.rmtree(temp_dir)


def test_aborting_message(setup_test_files):
    """Test that the command is aborted if no input is given when asking for overwriting permission."""
    temp_dir = setup_test_files
    runner = CliRunner()

    # Test file
    test_file = os.path.join(temp_dir, "file_1.pdf")

    result = runner.invoke(
        gsb,
        [
            "--compress=/screen",
            "--no_open_path",
            test_file,
        ],
    )

    # Check the output
    assert result.exit_code == 0
    assert "Aborting" in result.output


def test_copy_default_behavior(setup_test_files):
    """Test the default behavior of copying the file, ensuring the originals is preserved."""
    temp_dir = setup_test_files
    runner = CliRunner()

    # Test file
    test_file = os.path.join(temp_dir, "file_1.pdf")
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    result = runner.invoke(
        gsb,
        [
            "--compress=/ebook",
            f"--prefix={output_dir}{os.sep}compressed_",
            "--no_open_path",
            test_file,
        ],
    )

    # Check the output
    if result.exit_code != 0:
        print(f"Exit code: {result.exit_code}")
        print(f"Output: {result.output}")
        if result.exception:
            print(f"Exception: {result.exception}")
    assert result.exit_code == 0, f"Command failed with output: {result.output}"

    output_file = os.path.join(output_dir, "compressed_file_1.pdf")
    # List directory contents for debugging
    if not os.path.exists(output_file):
        print(f"Output file not found: {output_file}")
        print(f"Temp directory contents: {os.listdir(temp_dir)}")
        if os.path.exists(output_dir):
            print(f"Output directory contents: {os.listdir(output_dir)}")
        print(f"CLI output: {result.output}")

    assert os.path.exists(output_file), f"Output file does not exist. CLI output: {result.output}"
    assert os.path.getsize(output_file) > 0

    # Ensure the originals file is preserved
    originals_size = os.path.getsize(test_file)
    assert originals_size >= os.path.getsize(output_file)

    # time.sleep(1)


def test_force_overwrite_behavior(setup_test_files):
    """Test the behavior when `--force` is enabled to overwrite the originals file."""
    temp_dir = setup_test_files
    runner = CliRunner()

    # Test file
    test_file = os.path.join(temp_dir, "file_1.pdf")
    test_file_size = os.path.getsize(test_file)

    result = runner.invoke(
        gsb, ["--compress=/screen", "--force", "--no_open_path", test_file]
    )

    # Check the output
    assert result.exit_code == 0

    # Ensure the originals file is overwritten
    assert os.path.exists(test_file)
    new_size = os.path.getsize(test_file)
    assert new_size < test_file_size

    # time.sleep(2)


def test_keep_originals_when_smaller(setup_test_files):
    """Ensure that the originals file is kept if it is smaller than the new file."""
    temp_dir = setup_test_files
    runner = CliRunner()

    # Test file
    test_file = os.path.join(temp_dir, "file_2.pdf")
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    # convert in place the file to smallest size (well below the other distiller parameters),to ensure is smaller than another pass
    runner.invoke(
        gsb,
        [
            "--compress=/screen",
            "--options=-dColorImageResolution=10",
            "--force",
            "--no_open_path",
            test_file,
        ],
    )

    # actually run the command on the test file
    result = runner.invoke(
        gsb,
        [
            "--compress=/default",
            f"--prefix={output_dir}{os.sep}compressed_",
            "--no_open_path",
            test_file,
        ],
    )

    # Check the output
    assert result.exit_code == 0
    output_file = os.path.join(output_dir, "compressed_file_2.pdf")
    assert os.path.exists(output_file)

    # Ensure the originals file is kept if it's smaller than the new file (the new file has approximately the same size as the original)
    originals_size = os.path.getsize(test_file)
    new_size = os.path.getsize(output_file)
    # Allow small variations due to PDF metadata/encoding differences (timestamps, object ordering, etc.)
    assert abs(originals_size - new_size) < 100, f"File sizes differ by more than 100 bytes: original={originals_size}, new={new_size}"


def test_keep_new_when_larger(setup_test_files):
    """Test that the new file is kept when even if original is smaller."""
    temp_dir = setup_test_files
    runner = CliRunner()

    # Test file
    test_file = os.path.join(temp_dir, "file_3.pdf")
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    # convert in place the file to smallest size (well below the other distiller parameters),to ensure is smaller than another pass
    runner.invoke(
        gsb,
        [
            "--compress=/printer",
            # "--options='-dColorImageResolution=50'",
            "--force",
            "--no_open_path",
            test_file,
        ],
    )

    result = runner.invoke(
        gsb,
        [
            "--compress=/prepress",
            f"--prefix={output_dir}{os.sep}compressed_",
            "--pdfa=1",
            "--no_open_path",
            test_file,
        ],
    )

    # Check the output

    assert result.exit_code == 0

    output_file = os.path.join(output_dir, "compressed_file_3.pdf")

    # Ensure the new file is smaller and kept
    assert os.path.exists(test_file)
    new_size = os.path.getsize(output_file)
    assert new_size >= os.path.getsize(test_file)


def test_no_files_match_filter(setup_test_files):
    """Test graceful exit when no files match the filter."""
    temp_dir = setup_test_files
    runner = CliRunner()

    test_file = os.path.join(temp_dir, "file_1.pdf")

    result = runner.invoke(
        gsb,
        [
            "--compress=/screen",
            "--filter=png",  # No PNG files exist
            "--no_open_path",
            test_file,
        ],
    )

    # Should exit successfully (code 0)
    assert result.exit_code == 0
    assert "No files found" in result.output
    assert "Filter: png" in result.output
    # Should not show "Processing X file(s)"
    assert "Processing 0 file(s)" not in result.output


def test_empty_file_list_verbose(setup_test_files):
    """Test verbose output when no files match."""
    temp_dir = setup_test_files
    runner = CliRunner()

    test_file = os.path.join(temp_dir, "file_1.pdf")

    result = runner.invoke(
        gsb,
        [
            "--compress=/screen",
            "--filter=docx",
            "--verbose",
            "--no_open_path",
            test_file,
        ],
    )

    assert result.exit_code == 0
    assert "No files found" in result.output
    assert "Searched 1 path(s), found 0 matching files" in result.output


def test_recursive_search_nested_directories(setup_test_files):
    """Test recursive search finds files in nested directories."""
    temp_dir = setup_test_files
    runner = CliRunner()

    # Create nested directory structure with PDFs
    nested_dir = os.path.join(temp_dir, "subdir1", "subdir2")
    os.makedirs(nested_dir, exist_ok=True)

    # Copy a test file to nested location
    originals_dir = "tests/assets/originals"
    shutil.copy(
        os.path.join(originals_dir, "file_1.pdf"),
        os.path.join(nested_dir, "nested_file.pdf")
    )

    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    # Run with recursive flag
    result = runner.invoke(
        gsb,
        [
            "--compress=/screen",
            f"--prefix={output_dir}{os.sep}",
            "--recursive",
            "--no_open_path",
            temp_dir,
        ],
    )

    assert result.exit_code == 0
    # Should find all PDFs: 3 in root + 1 in nested dir = 4 files
    assert "Processing 4 file(s)" in result.output


def test_non_recursive_directory_search(setup_test_files):
    """Test non-recursive search only finds files in top level."""
    temp_dir = setup_test_files
    runner = CliRunner()

    # Create nested directory with PDF
    nested_dir = os.path.join(temp_dir, "subdir")
    os.makedirs(nested_dir, exist_ok=True)

    originals_dir = "tests/assets/originals"
    shutil.copy(
        os.path.join(originals_dir, "file_1.pdf"),
        os.path.join(nested_dir, "nested_file.pdf")
    )

    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    # Run WITHOUT recursive flag
    result = runner.invoke(
        gsb,
        [
            "--compress=/screen",
            f"--prefix={output_dir}{os.sep}",
            "--no_open_path",
            temp_dir,
        ],
    )

    assert result.exit_code == 0
    # Should only find 3 PDFs in root (not the nested one)
    assert "Processing 3 file(s)" in result.output


def test_mixed_file_and_directory_arguments(setup_test_files):
    """Test mixing direct file paths and directories with recursion."""
    temp_dir = setup_test_files
    runner = CliRunner()

    # Create a subdirectory with a PDF
    subdir = os.path.join(temp_dir, "subdir")
    os.makedirs(subdir, exist_ok=True)

    originals_dir = "tests/assets/originals"
    shutil.copy(
        os.path.join(originals_dir, "file_2.pdf"),
        os.path.join(subdir, "sub_file.pdf")
    )

    # Direct file path
    direct_file = os.path.join(temp_dir, "file_1.pdf")

    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    # Run with both a direct file and a directory
    result = runner.invoke(
        gsb,
        [
            "--compress=/screen",
            f"--prefix={output_dir}{os.sep}",
            "--recursive",
            "--no_open_path",
            direct_file,
            subdir,
        ],
    )

    assert result.exit_code == 0
    # Should find 1 direct file + 1 in subdir = 2 files
    assert "Processing 2 file(s)" in result.output
