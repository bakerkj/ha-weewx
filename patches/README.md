# patches/

Standard mechanism for applying small fixes to the WeeWX environment that don't
quite work as-is in our Python 3 / WeeWX 5 / addon image. Three parallel
subdirectories, one per _target tree_:

- `extensions/` — bundled user extensions installed under
  `/opt/weewx-data/bin/user/` (the things `weectl extension install` drops in,
  driven by `build/extensions.txt`).
- `weewx/` — WeeWX core libraries (`weedb`, `weewx`, …), pip-installed into the
  `/opt/weewx` venv's site-packages.
- `venv/` — the MQTT publisher (by felddy) — the `weewx_ha` pip package, also in
  the venv, separated so the patch paths can be relative to the package dir.

All three apply with `patch -p1` and share the same conventions for naming and
file contents.

## Convention (all subdirs)

- One file per fix, named `NNNN-short-description.patch`. Numbers are applied in
  lexical order (use `0001`, `0002`, …, `9999`) within each subdir.
- Each patch is a unified diff (`diff -u`) whose paths are **relative to the
  application root** for that subdir (see per-subdir notes below).
- The first line of the patch (after the diff header) should be a `# ` comment
  summarising why the patch exists and what upstream version it applies against.
  Doesn't have to be syntactic — `patch(1)` ignores leading lines that don't
  match the diff format.

## `extensions/` — bundled user extensions in `/opt/weewx-data`

- Paths are **relative to `/opt/weewx-data/`** — so a patch to
  `/opt/weewx-data/bin/user/foo.py` references it as `bin/user/foo.py`.
- The Dockerfile applies each `patches/extensions/*.patch` with `patch -p1` from
  `/opt/weewx-data/`, after all extensions have been installed.

## `weewx/` — patches for WeeWX core (`weedb`, `weewx`, …)

WeeWX core itself is installed as a pip distribution in the `/opt/weewx` venv's
`site-packages` and isn't reached by the `extensions/` loop. The Dockerfile
resolves the site-packages directory at build time from `weedb`
(`python3 -c 'import os, weedb; print(os.path.dirname(os.path.dirname(weedb.__file__)))'`)
so the patch is not tied to a Python version, then applies each
`patches/weewx/*.patch` there with `patch -p1`. Paths are **relative to that
site-packages directory** (a patch to `weedb/mysql.py` references it as
`weedb/mysql.py`).

## `venv/` — patches for pip-installed packages

Some bundled pieces are installed as **pip packages in the venv at
`/opt/weewx`**, not under `/opt/weewx-data` — notably the MQTT publisher's
`weewx_ha`
([felddy/weewx-home-assistant](https://github.com/felddy/weewx-home-assistant)).
Those can't be reached by the `extensions/` loop, so their patches live in
`patches/venv/`:

- Paths are **relative to the package directory** (a fix to
  `weewx_ha/config_publisher.py` references it as `config_publisher.py`).
- The Dockerfile resolves the package directory at build time
  (`python3 -c 'import os, weewx_ha; print(os.path.dirname(weewx_ha.__file__))'`),
  so the path is not tied to a Python version, then applies each
  `patches/venv/*.patch` there with `patch -p1`.

## Lifecycle

The Dockerfile bind-mounts `patches/` into the build and runs `patch` over each
`.patch` file in lexical order within each subdir, **after** all extensions have
been installed. A failing `patch` aborts the build (no silent skips).

## Generating a new patch (extensions example)

1. `docker run --rm ha-weewx:test bash -c 'cat /opt/weewx-data/bin/user/foo.py' > /tmp/foo.orig.py`
2. Hand-edit `/tmp/foo.new.py`.
3. `diff -u /tmp/foo.orig.py /tmp/foo.new.py > patches/extensions/00NN-foo-fix-x.patch`
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
