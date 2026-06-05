# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Manual install of the realtime-gauge-data extension.

Its ``install.py`` uses ``distutils`` (removed in Python 3.12) and the old
WeeWX 3/4 ``ExtensionInstaller`` API, so ``weectl extension install``
chokes on it. We just unpack the two pieces directly:

  - ``bin/user/rtgd.py``
  - ``skins/RealtimeGauges/`` (whole directory tree)
"""

import io
import os
import urllib.request
import zipfile

URL = "https://github.com/hoetzgit/weewx-realtime_gauge-data/archive/v0.6.0.zip"
PREFIX = "weewx-realtime_gauge-data-0.6.0/"
DEST_ROOT = "/opt/weewx-data"


def main() -> None:
    print(f"Manually installing realtime-gauge-data from {URL}")

    with urllib.request.urlopen(URL) as r:
        data = r.read()

    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in z.namelist():
            if name == PREFIX + "bin/user/rtgd.py":
                dest = os.path.join(DEST_ROOT, "bin/user/rtgd.py")
                with open(dest, "wb") as f:
                    f.write(z.read(name))
                print(f"  Copied {name} -> {dest}")
            elif name.startswith(
                PREFIX + "skins/RealtimeGauges/"
            ) and not name.endswith("/"):
                rel = name[len(PREFIX + "skins/RealtimeGauges/") :]
                dest = os.path.join(DEST_ROOT, "skins/RealtimeGauges", rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(z.read(name))
                print(f"  Copied {name} -> {dest}")


if __name__ == "__main__":
    main()
