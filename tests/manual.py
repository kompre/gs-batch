from gs_batch.gs_batch import gs_batch as gsb

from click.testing import CliRunner

import glob

files = glob.glob("tests/assets/originals/*3*")

runner = CliRunner()
result = runner.invoke(
    gsb,
    [
        "--compress=/ebook",
        "--prefix=output/compressed_",
        # "--pdfa=2",
        # "--options=-dCompatibilityLevel=1.5 -dColorImageResolution=1",
        "-v",
    ] + files,
)
print(result.output)