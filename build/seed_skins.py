# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Copy WeeWX's stock skins + user-package stubs into WEEWX_ROOT.

Stock skins (Seasons, Standard, Mobile, …) live in the weewx pip package's
``weewx_data/skins`` dir. The default template enables SeasonsReport, and
weewxd resolves SKIN_ROOT relative to WEEWX_ROOT — without this, a default
install crashes with ``skins/Seasons: No such file or directory``.

User stubs (``extensions.py``, ``__init__.py``) come from WeeWX's
``weewx_data/bin/user``. We build ``bin/user`` with ``weectl extension
install`` rather than ``weectl station create``, so these are never placed
and weewxd logs *"Cannot load user extensions: No module named
'user.extensions'"* at every startup.

Existing entries are never overwritten (extensions installed in either
location win).
"""

import os
import shutil

import weewx

DEST_ROOT = "/opt/weewx-data"


def main() -> None:
    site_packages = os.path.dirname(os.path.dirname(weewx.__file__))

    skin_src = os.path.join(site_packages, "weewx_data", "skins")
    skin_dst = os.path.join(DEST_ROOT, "skins")
    for name in sorted(os.listdir(skin_src)):
        s = os.path.join(skin_src, name)
        d = os.path.join(skin_dst, name)
        if os.path.isdir(s) and not os.path.exists(d):
            shutil.copytree(s, d)
            print(f"Copied stock skin {name} -> {d}")

    user_src = os.path.join(site_packages, "weewx_data", "bin", "user")
    user_dst = os.path.join(DEST_ROOT, "bin", "user")
    os.makedirs(user_dst, exist_ok=True)
    for name in ("extensions.py", "__init__.py"):
        s = os.path.join(user_src, name)
        d = os.path.join(user_dst, name)
        if os.path.exists(s) and not os.path.exists(d):
            shutil.copy2(s, d)
            print(f"Copied stock user stub {name} -> {d}")


if __name__ == "__main__":
    main()
