from gs_batch.gs_batch import gs_batch as gsb

from click.testing import CliRunner

runner = CliRunner()
result = runner.invoke(
    gsb, 
    [
        './tests/asset/mat.pdf', 
        '--compress',
        # '--prefix=mat_',
    ], 
)
print(result.output)

