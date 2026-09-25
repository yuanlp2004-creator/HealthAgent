"""Run all twenty module-two cases by default."""
from pathlib import Path
import runpy
import sys


if __name__ == '__main__':
    if len(sys.argv) == 1 or sys.argv[1].startswith('-'):
        sys.argv.insert(1, 'module2')
    runpy.run_path(str(Path(__file__).resolve().parent / '第一批_袁立沛' / 'run_checks.py'),
                   run_name='__main__')
