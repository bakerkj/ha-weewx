# patches/

Standard mechanism for applying small fixes to bundled WeeWX extensions that
don't quite work as-is in our Python 3 / WeeWX 5 / addon environment.

## Convention

- One file per fix, named `NNNN-short-description.patch`. Numbers are applied in
  lexical order (use `0001`, `0002`, …, `9999`).
- Each patch is a unified diff (`diff -u`) with paths **relative to
  `/opt/weewx-data/`** — so a patch to a bundled extension in
  `/opt/weewx-data/bin/user/foo.py` references it as `bin/user/foo.py`.
- The first line of the patch (after the diff header) should be a `# ` comment
  summarising why the patch exists and what upstream version it applies against.
  Doesn't have to be syntactic — the patch tool ignores leading lines that don't
  match the diff format.
- Patches are applied with `patch -p1` from `/opt/weewx-data/`.

## `venv/` — patches for pip-installed packages

Some bundled pieces are installed as **pip packages in the venv at
`/opt/weewx`**, not under `/opt/weewx-data` — notably `weewx_ha`
(felddy/weewx-home-assistant). Those can't be reached by the `/opt/weewx-data`
loop, so their patches live in `patches/venv/`:

- Paths are **relative to the package directory** (a fix to
  `weewx_ha/config_publisher.py` references it as `config_publisher.py`).
- The Dockerfile resolves the package directory at build time
  (`python3 -c 'import os, weewx_ha; print(os.path.dirname(weewx_ha.__file__))'`),
  so the path is not tied to a Python version, then applies each
  `patches/venv/*.patch` there with `patch -p1`.
- Same `NNNN-short-description.patch` naming and leading `# ` rationale comment.

## Lifecycle

The Dockerfile copies `patches/` into the build context and runs `patch` over
each `.patch` file in lexical order, **after** all extensions have been
installed. A failing `patch` aborts the build (no silent skips).

## Generating a new patch

1. `docker run --rm ha-weewx:test bash -c 'cat /opt/weewx-data/bin/user/foo.py' > /tmp/foo.orig.py`
2. Hand-edit `/tmp/foo.new.py`.
3. `diff -u /tmp/foo.orig.py /tmp/foo.new.py > patches/00NN-foo-fix-x.patch`
4. Rewrite the `--- a/bin/user/foo.py` and `+++ b/bin/user/foo.py` headers so
   the path is relative to `/opt/weewx-data/`.
5. Add a leading comment line explaining the rationale.
6. Test with a clean build.

## Why `patch(1)` instead of inline `RUN sed`

Two things go wrong with `RUN sed`:

- Patches are invisible in code review (a one-line `RUN` often hides a
  multi-line code change behind escaped regex metacharacters).
- Reviewing what changed and why requires diffing the running image against
  upstream by hand. With `.patch` files the diff IS the fix.
