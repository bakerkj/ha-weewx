# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Download upstream weewx extensions, apply our patches, expose as importable
modules.

The 14 patches under ``patches/extensions/`` mutate upstream extensions that
are pulled down at Docker build time (``build/extensions.txt`` +
``build/install_rtgd.py``). For test purposes we mirror that step here: each
extension is downloaded once into a persistent cache under
``tests/_patched_extensions/<name>/``, our patches are applied with
``patch -p1``, and ``bin/user/`` is added to ``sys.path`` so ``import rtgd``,
``import previmeteo``, etc. resolve against the patched copy.

The cache directory is ``.gitignore``'d. To force a refresh, delete
``tests/_patched_extensions/<name>/``.
"""

from __future__ import annotations

import io
import pathlib
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from typing import Iterable

CACHE_ROOT = pathlib.Path(__file__).resolve().parent / "_patched_extensions"
PATCH_DIR = pathlib.Path(__file__).resolve().parent.parent / "patches" / "extensions"

# Each entry: module name -> (upstream zip URL, [patch filenames])
# URLs mirror build/extensions.txt and build/install_rtgd.py.
EXTENSIONS: dict[str, tuple[str, list[str]]] = {
    "previmeteo": (
        "https://github.com/previmeteo/weewx-previmeteo/archive/v0.1.zip",
        [
            "0001-previmeteo-py3-queue-shim.patch",
            "0005-previmeteo-qualify-get-site-dict.patch",
        ],
    ),
    "rtgd": (
        "https://github.com/hoetzgit/weewx-realtime_gauge-data/archive/v0.6.0.zip",
        [
            "0002-rtgd-verbose-thread-traceback.patch",
            "0007-rtgd-guard-start-of-day-reset.patch",
            "0011-rtgd-history-max-none-guard.patch",
            "0013-rtgd-fieldmap-deepcopy.patch",
            "0014-rtgd-tick-interval.patch",
        ],
    ),
    "purpleair": (
        "https://github.com/bakerkj/weewx-purpleair/archive/v0.10.zip",
        ["0003-purpleair-dedupe-consecutive-inserts.patch"],
    ),
    "forecast": (
        "https://github.com/chaunceygardiner/weewx-forecast/archive/v4.1.zip",
        ["0004-forecast-uppercase-zambretti-sql.patch"],
    ),
    "emoncms": (
        "https://github.com/matthewwall/weewx-emoncms/archive/7c04113.zip",
        ["0006-emoncms-skip-upload-abortedpost.patch"],
    ),
    "rtldavis": (
        "https://github.com/lheijst/weewx-rtldavis/archive/2f3b4b344fd70ab253aabfa837b0ffc76570c075.zip",
        [
            "0008-rtldavis-low-battery-regex.patch",
            "0009-rtldavis-python313-rstrings.patch",
            "0010-rtldavis-transmitters-override.patch",
            "0012-rtldavis-merge-last-seen.patch",
        ],
    ),
}


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url) as r:
        return r.read()


def _extract_module_only(zip_bytes: bytes, module: str, dest: pathlib.Path) -> None:
    """Extract just ``bin/user/<module>.py`` into ``<dest>/bin/user/<module>.py``.

    The upstream zips each have a single top-level directory whose name varies
    by ref; we discover it by inspection rather than hardcode.
    """
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = z.namelist()
    top_levels = {n.split("/", 1)[0] for n in names if "/" in n}
    if len(top_levels) != 1:
        raise RuntimeError(
            f"{module}: zip has unexpected layout (top dirs: {top_levels!r})"
        )
    prefix = next(iter(top_levels)) + "/"
    src_name = prefix + f"bin/user/{module}.py"
    if src_name not in names:
        raise RuntimeError(f"{module}: zip is missing {src_name!r}")
    dest_file = dest / "bin" / "user" / f"{module}.py"
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    dest_file.write_bytes(z.read(src_name))


def _apply(patch: pathlib.Path, root: pathlib.Path, reverse: bool = False) -> None:
    cmd = ["patch", "-p1", "--no-backup-if-mismatch", "-i", str(patch)]
    if reverse:
        cmd.insert(1, "-R")
    subprocess.run(cmd, cwd=root, check=True, capture_output=True)


def prepare(module: str, refresh: bool = False) -> pathlib.Path:
    """Materialise the patched ``bin/user/<module>.py`` and return its parent dir.

    Idempotent: a marker file records whether the cache is up to date, and the
    function is a no-op when called again with the same patches.
    """
    if module not in EXTENSIONS:
        raise KeyError(f"unknown extension {module!r}")
    url, patches = EXTENSIONS[module]
    root = CACHE_ROOT / module
    marker = root / ".patched_ok"

    if refresh and root.exists():
        shutil.rmtree(root)

    if marker.exists():
        return root / "bin" / "user"

    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    zip_bytes = _download(url)
    _extract_module_only(zip_bytes, module, root)
    for p in patches:
        _apply(PATCH_DIR / p, root)
    marker.write_text("ok\n")
    return root / "bin" / "user"


def revert(module: str, patch: str) -> None:
    """Reverse-apply a single patch against the cached source tree.

    Caller is responsible for restoring it (call :func:`reapply`) before
    returning to a clean state.
    """
    root = CACHE_ROOT / module
    _apply(PATCH_DIR / patch, root, reverse=True)
    _drop_module_from_sys_modules(module)


def reapply(module: str, patch: str) -> None:
    root = CACHE_ROOT / module
    _apply(PATCH_DIR / patch, root, reverse=False)
    _drop_module_from_sys_modules(module)


def _drop_module_from_sys_modules(module: str) -> None:
    sys.modules.pop(module, None)
    # Invalidate the cached .pyc; otherwise CPython may load the previous
    # bytecode after a patch revert/reapply if the mtime resolution missed
    # the change.
    pycache = CACHE_ROOT / module / "bin" / "user" / "__pycache__"
    if pycache.exists():
        shutil.rmtree(pycache)


def ensure_on_path(modules: Iterable[str]) -> None:
    """Prepare each extension and add its ``bin/user/`` to ``sys.path``."""
    for m in modules:
        bin_user = prepare(m)
        s = str(bin_user)
        if s not in sys.path:
            sys.path.insert(0, s)
