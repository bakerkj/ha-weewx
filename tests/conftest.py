# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

import pathlib
import sys

import pytest

# Make extensions/ importable as flat modules (mirrors runtime where the
# files live at /opt/weewx-data/bin/user/ and are imported as user.<name>).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "extensions"))

from tests._patched_sources import EXTENSIONS, ensure_on_path  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _stage_patched_extensions():
    """Download + patch every bundled upstream extension once per test session.

    The 14 patches in ``patches/extensions/`` mutate upstream extensions that
    are pulled down at Docker build time. For tests we mirror that step: each
    extension is downloaded once into a persistent ``.gitignore``'d cache
    under ``tests/_patched_extensions/`` and our patches are applied. The
    patched ``bin/user/`` directories are then placed on ``sys.path`` so
    ``import previmeteo``, ``import rtgd``, etc. resolve against the
    patched copy.
    """
    ensure_on_path(EXTENSIONS.keys())
