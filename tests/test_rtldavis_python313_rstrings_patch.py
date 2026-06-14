# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0009-rtldavis-python313-rstrings.patch.

Several ``re.compile()`` arguments in rtldavis.py contain unrecognised
escape sequences inside non-raw strings; Python 3.12+ emits a SyntaxWarning
for each at import time. The patch converts them to raw strings.

We compile the file with ``py_compile`` in a subprocess with
``-W error::SyntaxWarning`` so any remaining warning is promoted to a
``SyntaxError`` and the compile fails.
"""

import subprocess
import sys

from tests._patched_sources import prepare


def test_rtldavis_compiles_with_no_syntaxwarning():
    src_path = prepare("rtldavis") / "rtldavis.py"
    assert src_path.exists()

    code = (
        f"import py_compile, sys\npy_compile.compile({str(src_path)!r}, doraise=True)\n"
    )
    result = subprocess.run(
        [sys.executable, "-W", "error::SyntaxWarning", "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        "rtldavis.py must compile cleanly under -W error::SyntaxWarning; "
        "unprefixed regex strings raise SyntaxWarning on Py 3.12+ which "
        "noisies every weewxd start.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "SyntaxWarning" not in result.stderr, (
        f"unexpected SyntaxWarning surfaced:\n{result.stderr}"
    )
