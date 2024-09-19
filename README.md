# gs_batch

`gs_batch` is a command-line tool for batch processing PDF files using Ghostscript, applying the same set of gs options to all files specified while taking care of file renaming.

It offers convenient default settings for compression, PDF/A conversion, and you can also apply any custom Ghostscript options. 

## Features

- Batch process multiple PDF files
- Compress PDFs with various quality settings
- Convert PDFs to PDF/A format
- Apply custom Ghostscript options
- Multi-threaded processing for improved performance
- Progress tracking with tqdm
- Automatic file renaming with customizable prefixes and suffixes
- Option to keep either the smaller file or the new file after processing
- Cross-platform support (Windows, Linux, macOS)

## Installation

To install `gs_batch`, make sure you have Python 3.12+ and [pipx](https://github.com/pypa/pipx)^[`pipx` will let you install the package in a virtual environment, but the commands will be available from the command line] installed, then run:

```
pipx install git+https://github.com/kompre/gs-batch.git
```

Note: This tool requires Ghostscript to be installed on your system. Make sure you have Ghostscript installed and accessible from the command line.


## Usage

Basic usage:

`gs_batch` and the its alias `gsb` will be available from the command line.

```
gs_batch [OPTIONS] FILES...
```

Options:

- `--options TEXT`: Arbitrary Ghostscript options and switches.
- `--compress TEXT`: Compression quality level (e.g., /screen, /ebook, /printer, /prepress) (default: /ebook).
- `--pdfa INTEGER`: PDF/A version (1 for PDF/A-1, 2 for PDF/A-2, 3 for PDF/A-3; default: 2).
- `--prefix TEXT`: Prefix to add to the output file name.
- `--suffix TEXT`: Suffix to add to the output file name before the extension.
- `--keep_smaller / --keep_new`: Keep the smaller file between old and new (default: keep smaller).

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

After processing, gs_batch will display a summary table showing the original size, new size, compression ratio, and which file was kept for each processed PDF. The tool will also attempt to open the output folder in your default file manager.

## Requirements

- Python 3.6+
- Ghostscript
- click
- tqdm
- showinfm

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Acknowledgements

gs_batch uses Ghostscript for PDF processing. Ghostscript is released under the GNU Affero General Public License (AGPL).