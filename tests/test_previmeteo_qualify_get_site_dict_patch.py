# Copyright (c) 2026 Kenneth Baker <bakerkj@umich.edu>
# All rights reserved.

"""Behavioural regression test for
patches/extensions/0005-previmeteo-qualify-get-site-dict.patch.

Upstream previmeteo calls bare ``get_site_dict(...)``, which doesn't exist
at module scope. weewxd would crash at first ``StdPrevimeteo`` construction
with ``NameError``. The patch qualifies the call as
``weewx.restx.get_site_dict``.
"""

import importlib
import sys
from unittest.mock import Mock, patch


def test_stdprevimeteo_init_calls_qualified_get_site_dict():
    sys.modules.pop("previmeteo", None)
    previmeteo = importlib.import_module("previmeteo")

    # Stub ``weewx.restx.get_site_dict`` to return None so __init__ exits
    # cleanly before touching ``weewx.manager`` / queues / threads.
    with patch.object(
        previmeteo.weewx.restx, "get_site_dict", return_value=None
    ) as gsd:
        cfg = {"Previmeteo": {"station": "S", "password": "P"}}
        engine = Mock()
        # StdRESTful's __init__ just stashes engine + config; that's fine.
        svc = previmeteo.StdPrevimeteo(engine=engine, config_dict=cfg)
        assert svc is not None
        gsd.assert_called_once()
        args = gsd.call_args[0]
        # The patched call is
        #     weewx.restx.get_site_dict(
        #         config_dict, 'Previmeteo', 'station', 'password')
        assert args[0] is cfg
        assert args[1] == "Previmeteo"
        assert args[2] == "station"
        assert args[3] == "password"
