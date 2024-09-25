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

    # Copy test files to the temp directory
    for file_name in ["file_1.pdf", "file_2.pdf", "file_3.pdf"]:
        shutil.copy(os.path.join(originals_dir, file_name), temp_dir)

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
            f"--prefix={output_dir}/compressed_",
            "--no_open_path",
            test_file,
        ],
    )

    # Check the output
    assert result.exit_code == 0
    output_file = os.path.join(output_dir, "compressed_file_1.pdf")
    assert os.path.exists(output_file)
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
            "--options='-dColorImageResolution=10'",
            "--force",
            "--no_open_path",
            test_file,
        ],
    )

    # actually run the command on the test file
    result = runner.invoke(
        gsb,
        [
            "--compress=/screen",
            f"--prefix={output_dir}/compressed_",
            "--no_open_path",
            test_file,
        ],
    )

    # Check the output
    assert result.exit_code == 0
    output_file = os.path.join(output_dir, "compressed_file_2.pdf")
    assert os.path.exists(output_file)

    # Ensure the originals file is kept if it's smaller than the new file (the new file has the same size of the original)
    originals_size = os.path.getsize(test_file)
    new_size = os.path.getsize(output_file)
    assert originals_size == new_size


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
            f"--prefix={output_dir}/compressed_",
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
