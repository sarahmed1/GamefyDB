import os
import subprocess
import sys

PYTHON = sys.executable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _run(*args):
    """Run run.py with the given args, capturing output safely on Windows."""
    return subprocess.run(
        [PYTHON, 'run.py', *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=ROOT,
    )


def test_run_help():
    result = _run('--help')
    assert result.returncode == 0
    assert '--format' in result.stdout
    assert '--input' in result.stdout
    assert '--output' in result.stdout


def test_run_csv_output(tmp_path):
    result = _run('--input', 'excel', '--output', str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert os.path.isfile(os.path.join(tmp_path, 'dims', 'dim_cashier.csv'))
    assert os.path.isfile(os.path.join(tmp_path, 'facts', 'fact_cash_transactions.csv'))


def test_run_excel_output(tmp_path):
    result = _run('--input', 'excel', '--output', str(tmp_path), '--format', 'excel')
    assert result.returncode == 0, result.stderr
    assert os.path.isfile(os.path.join(tmp_path, 'gamefydb.xlsx'))
