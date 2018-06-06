import os.path

import pytest
import rstcheck
from .shared import PROJECT_ROOT_DIR

@pytest.mark.parametrize('rst_file', [
    'CONTRIBUTE.rst',
    'README.rst',
    'CHANGELOG.rst',
    'AUTHORS.rst',
    os.path.join('docs', 'cli.rst'),
    os.path.join('docs', 'index.rst'),
    os.path.join('docs', 'install.rst')
])
def test_rst(rst_file):
    rst_file = os.path.join(PROJECT_ROOT_DIR, rst_file)
    with open(rst_file) as input_file:
        contents = input_file.read()

    all_errors = []
    for error in rstcheck.check(contents, report_level=2, ignore={'languages': ['python', 'bash']}):
        # report only warnings and higher, ignore Python and Bash pseudocode examples
        if 'Title underline too short' in error[1]:
            # These are caused by unicode en dashes and can be ignored
            continue
        all_errors.append(error)

    assert len(all_errors) == 0
