# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function


import os
import shutil
import subprocess

from ..console import log
from ..wheel_cache import WheelCache
from .. import util


class CondaCache(WheelCache):
    def __init__(self, conf, root):
        self._root = root
        self._path = os.path.join(root, 'conda-cache')
        self._wheel_cache_size = getattr(conf, 'conda_cache_size', 0)
        self._extension = '.tar.bz2'

    def build_project_cached(self, env, package, commit_hash):
        if self._wheel_cache_size == 0:
            return None

        wheel = self._get_wheel(commit_hash)
        if wheel:
            return wheel

        self._cleanup_wheel_cache()

        fn = env.build_project(commit_hash)
        cache_path = self._create_wheel_cache_path(commit_hash)

        try:
            shutil.move(fn, cache_path)
        except subprocess.CalledProcessError:
            # failed -- clean up
            shutil.rmtree(cache_path)
            raise

        return self._get_wheel(commit_hash)
