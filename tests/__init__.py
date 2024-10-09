from gs_batch.gs_batch import gs_batch as gsb

from click.testing import CliRunner

import glob

files = glob.glob("tests/assets/originals/*.pdf")

runner = CliRunner()
result = runner.invoke(
    gsb,
    [
        "--compress=/ebook",
        "--prefix=../output/compressed_",
        "--pdfa=2",
        # "-v"
    ] + files,
)
print(result.output)

import subprocess
import time

# cmd = [
#     "gswin64c",
#     "-dPDFINFO",
#     "-dBATCH",
#     "-dNODISPLAY",
#     "tests/assets/originals/file_1.pdf",
# ]

# try:
#     result = subprocess.Popen(
#         cmd,
#         # stdin=subprocess.PIPE,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.STDOUT,
#         text=True,
#     )
# except subprocess.CalledProcessError as e:
#     print(e)

# # time.sleep(2)
    
# for l in result.stdout:
#     print(l)