# -*- coding: utf8 -*-
"""
放置taskflow相关内容
task放在task.py
flow放在flow.py
engine放在views.py
"""

import contextlib
from config import Config
from taskflow.persistence import backends

backend_uri = Config.TASKFLOW_DATABASE_URI
conf = {
    'connection': backend_uri,
}


def get_taskflow_backend():
    backend = backends.fetch(conf)
    with contextlib.closing(backend.get_connection()) as conn:
        conn.upgrade()
    return backend
