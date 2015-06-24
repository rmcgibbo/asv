# -*- coding: utf-8 -*-
# Licensed under a 3-clause BSD style license - see LICENSE.rst

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import six

import os
import platform
import sys
import textwrap

from . import console
from . import util


def iter_machine_files(results_dir):
    """
    Iterate over all of the machine.json files in the results_dir
    """
    for root, dirs, files in os.walk(results_dir):
        for filename in files:
            if filename == 'machine.json':
                path = os.path.join(root, filename)
                yield path


def _get_unique_machine_name():
    (system, node, release, version, machine, processor) = platform.uname()
    return node


class MachineCollection(object):
    """
    Stores information about 1 or more machines in the
    ~/.asv-machine.json file.
    """
    api_version = 1

    @staticmethod
    def get_machine_file_path():
        return os.path.expanduser('~/.asv-machine.json')

    @classmethod
    def load(cls, machine_name, _path=None):
        if _path is None:
            path = cls.get_machine_file_path()
        else:
            path = _path

        d = {}
        if os.path.isfile(path):
            d = util.load_json(path, cls.api_version)
            if machine_name in d:
                return d[machine_name]
            elif len(d) == 1 and machine_name == _get_unique_machine_name():
                return d[list(d.keys())[0]]

        raise util.UserError(
            "No information stored about machine '{0}'. I know about {1}.".format(
                machine_name, util.human_list(d.keys())))

    @classmethod
    def save(cls, machine_name, machine_info, _path=None):
        if _path is None:
            path = cls.get_machine_file_path()
        else:
            path = _path
        if os.path.isfile(path):
            d = util.load_json(path)
        else:
            d = {}
        d[machine_name] = machine_info
        util.write_json(path, d, cls.api_version)

    @classmethod
    def update(cls):
        path = cls.get_machine_file_path()
        if os.path.isfile(path):
            util.update_json(cls, path, cls.api_version)


class Machine(object):
    """
    Stores information about a particular machine.
    """
    api_version = 1

    fields = [
        ("machine",
         """
         A unique name to identify this machine in the results.  May
         be anything, as long as it is unique across all the machines used
         to benchmark this project.

         NOTE: If changed from the default, it will no longer match
         the hostname of this machine, and you may need to explicitly
         use the --machine argument to asv.
         """),

        ("os",
         """
         The OS type and version of this machine.  For example,
         'Macintosh OS-X 10.8'."""),

        ("arch",
         """
         The generic CPU architecture of this machine.  For
         example, 'i386' or 'x86_64'."""),

        ("cpu",
         """
         A specific description of the CPU of this machine,
         including its speed and class.  For example, 'Intel(R)
         Core(TM) i5-2520M CPU @ 2.50GHz (4 cores)'."""),

        ("ram",
         """
         The amount of physical RAM on this machine.  For example,
         '4GB'."""),

        ("gpu",
         """
         The type of GPU in the machine, and/or driver information. 
         For example, 'NVIDIA GTX TITAN'
         """),
    ]

    hardcoded_machine_name = None

    @classmethod
    def get_unique_machine_name(cls):
        if cls.hardcoded_machine_name:
            return cls.hardcoded_machine_name
        return _get_unique_machine_name()

    @staticmethod
    def get_defaults():
        (system, node, release, version, machine, processor) = platform.uname()

        cpu = util.get_cpu_info()

        ram = six.text_type(util.get_memsize())

        return {
            'machine': node,
            'os': "{0} {1}".format(system, release),
            'arch': platform.machine(),
            'cpu': cpu,
            'ram': ram,
            'gpu': '',
            }

    @staticmethod
    def generate_machine_file():
        if not sys.stdout.isatty():
            raise util.UserError(
                "Run asv at the console the first time to generate "
                "one.")

        print("I will now ask you some questions about this machine to "
              "identify it in the benchmarks.")
        print()

        defaults = Machine.get_defaults()
        values = {}

        for i, (name, description) in enumerate(Machine.fields):
            print(
                textwrap.fill(
                    '{0}. {1}: {2}'.format(
                        i+1, name, textwrap.dedent(description)),
                    subsequent_indent='   '))
            values[name] = console.get_answer_default(name, defaults[name])

        return values

    @classmethod
    def load(cls, interactive=False, force_interactive=False, _path=None,
             machine_name=None, **kwargs):
        self = Machine()

        if machine_name is None:
            machine_name = cls.get_unique_machine_name()
        try:
            d = MachineCollection.load(machine_name, _path=_path)
        except util.UserError as e:
            console.log.error(str(e) + '\n')
            d = {}
        d.update(kwargs)
        if (not len(d) and interactive) or force_interactive:
            d.update(self.generate_machine_file())

        machine_name = d['machine']

        self.__dict__.update(d)
        MachineCollection.save(machine_name, self.__dict__, _path=_path)
        return self

    def save(self, results_dir):
        path = os.path.join(results_dir, self.machine, 'machine.json')
        util.write_json(path, self.__dict__, self.api_version)

    @classmethod
    def update(cls, path):
        util.update_json(cls, path, cls.api_version)
