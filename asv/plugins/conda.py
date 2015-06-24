# Licensed under a 3-clause BSD style license - see LICENSE.rst
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, unicode_literals, print_function

import os
import tempfile
import subprocess

import six

from .. import environment
from ..console import log
from .. import util
from . import conda_cache


class Conda(environment.Environment):
    """
    Manage an environment using conda.

    Dependencies are installed using ``conda``.  The benchmarked
    project is installed using ``pip`` (since ``conda`` doesn't have a
    method to install from an arbitrary ``setup.py``).
    """
    tool_name = "conda"

    def __init__(self, conf, python, requirements):
        """
        Parameters
        ----------
        conf : Config instance

        python : str
            Version of Python.  Must be of the form "MAJOR.MINOR".

        requirements : dict
            Dictionary mapping a PyPI package name to a version
            identifier string.
        """
        self._python = python
        self._requirements = requirements
        super(Conda, self).__init__(conf)
        self._conda_recipe = getattr(conf, 'conda_recipe_dir', 'conda-recipe')
        self._cache = conda_cache.CondaCache(conf, self._path)

    def build_project(self, commit_hash):
        self.checkout_project(commit_hash)
        conda_build = util.which('conda-build')
        log.info("Building for {0}\n".format(self.name))

        environ=dict(**os.environ)
        environ['SOURCE_PATH'] = self._build_root
        try:
            subprocess.check_call([
                conda_build,
                self._conda_recipe,
                '--no-binstar-upload', '--no-test',
                '--python', self._python,
            ], env=environ)
        except (subprocess.CalledProcessError, KeyboardInterrupt) as e:
            self._run_conda(['clean', '--lock'])
            raise e

        fn = subprocess.check_output([
            conda_build,
            self._conda_recipe,
            '--python', self._python,
            '--output'], env=environ).decode('utf-8').strip()
        return fn

    @classmethod
    def matches(self, python):
        try:
            conda = util.which('conda')
        except IOError:
            return False
        else:
            # This directory never gets created, since we're just
            # doing a dry run below.  All it needs to be is something
            # that doesn't already exist.
            path = os.path.join(tempfile.gettempdir(), 'check')
            # Check that the version number is valid
            try:
                util.check_call([
                    conda,
                    'create',
                    '--yes',
                    '-p',
                    path,
                    'python={0}'.format(python),
                    '--dry-run'], display_error=False)
            except util.ProcessError:
                return False
            else:
                return True

    @classmethod
    def get_environments(cls, conf, python):
        for configuration in environment.iter_configuration_matrix(conf.matrix):
            yield cls(conf, python, configuration)

    def check_presence(self):
        if not super(Conda, self).check_presence():
            return False
        for fn in ['pip', 'python']:
            if not os.path.isfile(os.path.join(self._path, 'bin', fn)):
                return False
        try:
            self._run_executable('python', ['-c', 'pass'])
        except (subprocess.CalledProcessError, OSError):
            return False
        return True

    def install_project(self, conf, commit_hash=None):
        if commit_hash is None:
            commit_hash = self._cache.get_existing_commit_hash()
            if commit_hash is None:
                commit_hash = self.repo.get_hash_from_master()

                # self.uninstall(conf.project)

        build_bz2 = self._cache.build_project_cached(
            self, conf, commit_hash)

        if build_bz2 is None:
            build_bz2 = self.build_project(commit_hash)
        self.install(build_bz2)

    def _setup(self):
        try:
            conda = util.which('conda')
        except IOError as e:
            raise util.UserError(str(e))

        log.info("Creating conda environment for {0}".format(self.name))
        util.check_call([
            conda,
            'create',
            '--yes',
            '-p',
            self._path,
            '--use-index-cache',
            'python={0}'.format(self._python)])

    def _run_executable(self, executable, args, **kwargs):
        if util.WIN:
            if executable == 'python':
                path = os.path.join(self._path, 'python.exe')
            else:
                path = os.path.join(self._path, 'Scripts', executable + '.exe')
            return util.check_output([path] + args, **kwargs)
        else:
            return util.check_output([
                os.path.join(self._path, 'bin', executable)] + args, **kwargs)

    def install(self, package):
        log.info("Installing {0} into {1}".format(os.path.basename(package), self.name))
        stdout = self._run_conda(['install', '-y', package, '-p', self._path])
        print(stdout)

    def uninstall(self, packauge):
        log.info("Uninstalling from {0}".format(self.name))
        stdout = self._run_conda(['uninstall', '-y', package, '-p', self._path],
                             valid_return_codes=None)
        print(stdout)

    def run(self, args, **kwargs):
        log.debug("Running '{0}' in {1}".format(' '.join(args), self.name))
        return self._run_executable('python', args, **kwargs)

    def _run_conda(self, args, **kwargs):
        conda = util.which('conda')
        return util.check_output([conda] + args, **kwargs)
