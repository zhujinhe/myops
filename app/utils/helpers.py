# -*- coding: utf8 -*-
import os


def get_full_path(file_path, file_name):
    basedir = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(
        os.path.dirname(__file__)))))
    full_path = os.path.join(basedir, file_path, file_name)
    return full_path
