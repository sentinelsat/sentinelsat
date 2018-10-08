import re
from glob import glob

import os.path
import pytest
import rstcheck

from .shared import PROJECT_ROOT_DIR

rst_files = list(glob(os.path.join(PROJECT_ROOT_DIR, '*.rst')))
rst_files += list(glob(os.path.join(PROJECT_ROOT_DIR, 'docs', '*.rst')))


@pytest.mark.parametrize('rst_file', rst_files)
def test_rst(rst_file):
    with open(rst_file) as input_file:
        contents = input_file.read()

    all_errors = []
    errors = rstcheck.check(
        contents,
        report_level=2,
        ignore={
            'languages': ['python', 'bash']
        }
    )
    for line_number, error in errors:
        # report only warnings and higher, ignore Python and Bash pseudocode examples
        if 'Title underline too short' in error:
            # These are caused by unicode en dashes and can be ignored
            continue

        # Ignore to text roles provided via Sphinx extensions erroneously marked as unrecognized
        m = re.search('Unknown interpreted text role "([^"]+)"', error)
        if m and m.group(1) in ['program', 'paramref']:
            continue

        m = re.search('Unknown directive type "([^"]+)"', error)
        if m and m.group(1) in ['automodule']:
            continue

        all_errors.append((line_number, error))

    assert len(all_errors) == 0
