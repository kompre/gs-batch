# gs-batch-pdf

`gs-batch-pdf` is a command-line tool for batch (parallel) processing PDF files using [Ghostscript](https://www.ghostscript.com/), applying the same set of gs options to all files specified while taking care of file renaming.

It offers convenient default settings for compression, PDF/A conversion, and you can also apply any custom Ghostscript options. 

## Features

- Batch process multiple PDF files
- Compress PDFs with various quality settings
- Convert PDFs to PDF/A format[^1]
- Apply custom Ghostscript options
- Multi-threaded processing for improved performance
- Progress tracking with tqdm
- Automatic file renaming with customizable prefixes and suffixes
- Option to keep either the smaller file or the new file after processing
- Cross-platform support (Windows, Linux, macOS)

[^1]: you need to use gs version 10.04.0 or higher for correct PDF/A level 2 or 3 conversion.

## Installation

To install `gs-batch-pdf`, make sure you have Python 3.12+ and [pipx](https://pipx.pypa.io/stable/)[^2] installed, then run:

[^2]:`pipx` will let you install the package in a virtual environment, but the commands will be available from the command line

```
pipx install gs-batch-pdf
```

Note: This tool requires Ghostscript to be installed on your system. Make sure you have Ghostscript installed and accessible from the command line.


## Usage

Basic usage:

`gs_batch` and the its alias `gsb` will be available from the command line.

```
gs-batch-pdf [OPTIONS] FILES...
```

Options:

- `--options TEXT`: Arbitrary Ghostscript options and switches.
- `--compress TEXT`: Compression quality level (e.g., /screen, /ebook, /printer, /prepress) (default: /ebook).
- `--pdfa INTEGER`: PDF/A version (1 for PDF/A-1, 2 for PDF/A-2, 3 for PDF/A-3; default: 2).
- `--prefix TEXT`: Prefix to add to the output file name.
- `--suffix TEXT`: Suffix to add to the output file name before the extension.
- `--keep_smaller / --keep_new`: Keep the smaller file between old and new (default: keep smaller).
- `--force`: Allow overwriting the original file.

## Examples

1. Compress multiple PDF files using ebook quality:

```
gs_batch --compress=/ebook file1.pdf file2.pdf file3.pdf
```

2. Convert PDFs to PDF/A-2 format:

```
gs_batch --pdfa=2 file1.pdf file2.pdf
```

3. Compress and Convert PDFs to PDF/A-2 format all pdfs in a folder:

```
# you can use glob patterns
gs_batch --compress --pdfa=2 *.pdf 
```

4. Apply custom Ghostscript options:

```
gs_batch --options="-dPDFSETTINGS=/screen -dColorImageResolution=72" file.pdf
```

4. Add prefix^[you can also specify new folder] and suffix to output files:

```
gs_batch --prefix="./compressed/" --suffix="_v1" --compress=/screen file*.pdf 
```

## Output

After processing, gs-batch-pdf will display a summary table showing the original size, new size, compression ratio, and which file was kept for each processed PDF. The tool will also attempt to open the output folder in your default file manager.

## Requirements

- Python 3.12+
- Ghostscript
- click
- tqdm
- showinfm

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Acknowledgements

gs-batch-pdf uses Ghostscript for PDF processing. Ghostscript is released under the GNU Affero General Public License (AGPL).