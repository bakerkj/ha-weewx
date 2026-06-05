# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

import pathlib
import sys

# Make extensions/ importable as flat modules (mirrors runtime where the
# files live at /opt/weewx-data/bin/user/ and are imported as user.<name>).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "extensions"))
