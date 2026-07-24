# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Guard rail for build/extensions.txt.

Every URL line in ``build/extensions.txt`` must be preceded by at least
one ``# install: <path>`` annotation within the same paragraph (i.e.
no blank line between the annotation block and the URL). Those
annotations are what ``build/check_image.sh`` reads to synthesise the
in-image presence assertions for each installed extension — drop the
annotation and the assertion silently disappears, so a broken or
missing install ships undetected.

Run via pre-commit (see ``.pre-commit-config.yaml``) and in CI from the
``build-checks`` job in ``.github/workflows/tests.yaml``.

Exits 0 on success, 1 on the first unannotated URL (with the line
number and URL printed to stderr).
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / "extensions.txt"


def check(path: Path) -> list[str]:
    """Return a list of human-readable error strings; empty == success."""
    errors: list[str] = []
    # Annotations carry over until either a blank line or a URL line
    # consumes them. A URL with an empty pending set is an error.
    pending_annotations: list[int] = []  # line numbers, for diagnostics
    for lineno, raw in enumerate(path.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line:
            # blank line resets the paragraph — annotations don't cross
            # blank lines (matches the parser in check_image.sh, which
            # reads only `# install:` immediately above the URL).
            pending_annotations = []
            continue
        if line.startswith("# install:"):
            pending_annotations.append(lineno)
            continue
        if line.startswith("#"):
            # other comments don't reset the paragraph and don't count
            # as annotations; they're just prose.
            continue
        # Non-blank, non-comment line: treat as a URL.
        if not pending_annotations:
            errors.append(
                f"{path}:{lineno}: URL has no preceding '# install: <path>' "
                f"annotation in its paragraph: {line}"
            )
        # Consume the annotations regardless — a single URL can have
        # multiple `# install:` lines (e.g. forecast emits both a
        # module and a skin) but each URL starts fresh.
        pending_annotations = []
    return errors


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv[1:]] or [DEFAULT_PATH]
    rc = 0
    for p in paths:
        for err in check(p):
            print(err, file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
