
#
# Copyright (c) 2021 Raspberry Pi (Trading) Ltd.
#
# SPDX-License-Identifier: BSD-3-Clause
#

"""
picogenlib -- functions used for generating Pico project files to be used by the CLI or by a GUI
"""

import json
import platform
import shutil
from enum import Enum
from pathlib import Path
import os
import subprocess
import sys
from collections.abc import Callable
from jinja2 import Environment, FileSystemLoader, pass_context

# constants that need to be put somewhere else
CMAKELIST_FILENAME = 'CMakeLists.txt'
COMPILER_NAME = 'arm-none-eabi-gcc'

VSCODE_LAUNCH_FILENAME = 'launch.json'
VSCODE_C_PROPERTIES_FILENAME = 'c_cpp_properties.json'
VSCODE_SETTINGS_FILENAME = 'settings.json'
VSCODE_EXTENSIONS_FILENAME = 'extensions.json'
VSCODE_FOLDER = '.vscode'

# Custom Jinja filters (can be refactored)


@pass_context
def jinja_find_define(context, peripheral_name, *args, **kwargs):
    func = getattr(context.vars['fragments'], f'{peripheral_name}_define')
    return func(*args, **kwargs)


@pass_context
def jinja_find_initialiser(context, peripheral_name, *args, **kwargs):
    func = getattr(context.vars['fragments'], f'{peripheral_name}_initialiser')
    return func(*args, **kwargs)


class IDE(Enum):
    VSCODE = 'vscode'
    NO_IDE = None


class LibInfo(Enum):
    GUI_TEXT = 0
    C_FILE = 1
    H_FILE = 2
    LIB_NAME = 3


class PicoProjectFactory():
    """
    Programatically generates a Pico project. To be used as a singleton class.
    """

    def __init__(self, base_path, kwargs, has_gui=None):
        # options pertaining to cmake and builds
        self.build_opts = {
            "wants_uart": kwargs['uart'],
            "wants_usb": kwargs['usb'],
            "wants_run_from_ram": kwargs['runFromRAM'],
            "wants_cpp": kwargs['cpp'],
            "exceptions": kwargs['cppexceptions'],
            "configs": kwargs['configs'],
            "rtti": kwargs['cpprtti']
        }
        # options pertaining to the Pico code
        self.code_opts = {
            "features": kwargs['feature'],
            "wants_examples": kwargs['examples']
        }
        # options for Pico project generation
        self.project_opts = {
            "base_path": kwargs['project_root'],
            "name": kwargs['name'],
            "wants_overwrite": kwargs['overwrite'],
            "wants_build": kwargs['build']
        }
        # options for the IDE
        self.ide_opts = {
            "name": IDE(kwargs['project']),
            "debugger": kwargs['debugger'],

        }

        # pointer to Jinja env
        self.jinja_env = self._get_jinja_env(base_path / 'templates')
        self.constants = self.get_constants(base_path / 'constants.json')

        self.parent_gui = has_gui

    def _get_jinja_env(self, templates_path):
        """
        Configures the Jinja environment for loading our templates with our configs
        """
        jinja_env = Environment(loader=FileSystemLoader(templates_path))
        jinja_env.trim_blocks = True
        jinja_env.lstrip_blocks = True
        jinja_env.keep_trailing_newline = True

        jinja_env.filters['find_define'] = jinja_find_define
        jinja_env.filters['find_initialiser'] = jinja_find_initialiser

        return jinja_env

    @staticmethod
    def get_constants(path):
        with open(path, 'r') as f:
            constants = json.loads(f.read())
        return constants

    def run_cmake(self, callable: Callable = None):
        is_windows = platform.system() == 'Windows'
        project_path = self.project_opts['project_path']
        if is_windows:
            cmake_cmd = f'cmake -DCMAKE_BUILD_TYPE=Debug -G "NMake Makefiles" -S {project_path} -B {project_path / "build"}'
        else:
            cmake_cmd = f'cmake -DCMAKE_BUILD_TYPE=Debug -S {project_path} -B {project_path / "build"}'

        if callable:
            callable(cmake_cmd.split())
        else:
            subprocess.run(cmake_cmd.split(), shell=is_windows)

    def run_make(self, callable: Callable):
        old_dir = os.getcwd()
        os.chdir(self.project_opts['project_path'])
        is_windows = platform.system() == 'Windows'
        cpus = os.cpu_count() or 1
        if is_windows:
            makeCmd = 'nmake -j ' + str(cpus)
        else:
            makeCmd = 'make -j ' + str(cpus)

        if callable:
            callable(makeCmd)
        else:
            subprocess.Popen(makeCmd.split(), shell=True).wait()

        os.chdir(old_dir)

    def generate_main(self):
        """
        Generates the main C/C++ file
        """
        template = self.jinja_env.get_template('main.txt')
        mapping = dict(includes=[], libraries=[])

        features_list = self.constants['features_list']
        stdlib_examples_list = self.constants['stdlib_examples_list']
        features = self.code_opts['features']

        if self.code_opts['wants_examples']:
            features += list(stdlib_examples_list.keys())

        if features:
            includes = []
            for feat in features:
                if feat in features_list:
                    includes.append(features_list[feat][LibInfo.H_FILE.value])
                elif feat in stdlib_examples_list:
                    includes.append(stdlib_examples_list[feat][LibInfo.H_FILE.value])
            mapping['includes'] = includes

            # Add library names so we can lookup any defines or initialisers
            mapping['libraries'] = features

        extension = '.cpp' if self.build_opts['wants_cpp'] else '.c'
        filename = self.project_opts['project_path'] / (self.project_opts['name'] + extension)

        with open(filename, 'w') as f:
            f.write(template.render(mapping))

    def generate_cmake(self):
        filename = self.project_opts['project_path'] / CMAKELIST_FILENAME
        template = self.jinja_env.get_template("cmake.txt")

        copts = self.build_opts
        mapping = {
            # CMake will accept forward slashes on Windows, and that's
            # seemingly a bit easier to handle than the backslashes
            'sdk_path': str(copts['sdk_path']).replace('\\', '/'),
            'project_name': self.project_opts['name'],
            # add the preprocessor defines for overall configuration
            'configs': copts['configs'], 'exceptions': copts['exceptions'],
            'rtti': copts['rtti'], 'wants_cpp': copts['wants_cpp'], 'wants_run_from_ram': copts['wants_run_from_ram'],
            # Console output destinations
            'wants_uart': copts['wants_uart'], 'wants_usb': copts['wants_usb']
        }

        # selected libraries/features
        features = self.code_opts['features']
        features_list = self.constants['features_list']
        if features:
            mapping['features'] = features
            features_lib_names = []
            for feat in features:
                if feat in features_list:
                    features_lib_names.append(features_list[feat][LibInfo.LIB_NAME.value])
            mapping['features_list'] = features_lib_names

        with open(filename, 'w') as f:
            f.write(template.render(mapping))

    def generate_ide(self):
        args = []

        if self.ide_opts['name'] == IDE.VSCODE:
            deb = self.constants['debugger_config_list'][self.ide_opts['debugger']]
            vscode_path = self.project_opts['project_path'] / VSCODE_FOLDER
            if not vscode_path.is_dir():
                vscode_path.mkdir(exist_ok=True)

            args = [('vscode/launch.txt', VSCODE_LAUNCH_FILENAME, dict(deb=deb)),
                    ('vscode/c_properties.txt', VSCODE_C_PROPERTIES_FILENAME, dict()),
                    ('vscode/settings.txt', VSCODE_SETTINGS_FILENAME, dict()),
                    ('vscode/extensions.txt', VSCODE_EXTENSIONS_FILENAME, dict())]

        for template_name, file_name, mapping in args:
            template = self.jinja_env.get_template(template_name)
            mapping = dict(deb=deb)
            with open(vscode_path / file_name, 'w') as f:
                f.write(template.render(mapping))

    def generate_all(self):
        self.generate_main()
        self.generate_cmake()
        self.generate_ide()

    def setup_project(self):
        # create project dir
        project_path = self.project_opts['base_path'] / self.project_opts['name']
        project_path.mkdir(exist_ok=True)
        self.project_opts['project_path'] = project_path

    def setup_build_system(self):
        wants_overwrite = self.project_opts['wants_overwrite']
        cmake_exists = (self.project_opts['project_path'] / CMAKELIST_FILENAME).exists()
        if not wants_overwrite and cmake_exists:
            self.send_error(
                'There already appears to be a project in this folder. Use the --overwrite option or toggle overwrite in the GUI to overwrite.')

        # copy sdk import
        sdk_path = self.build_opts['sdk_path']
        project_path = self.project_opts['project_path']
        shutil.copyfile(sdk_path / 'external' / 'pico_sdk_import.cmake', project_path / 'pico_sdk_import.cmake')

        # create build dir
        (project_path / 'build').mkdir(exist_ok=True)

    def verify_build_system(self):
        # check existence of compiler
        if not shutil.which(COMPILER_NAME):
            m = 'Unable to find the `' + COMPILER_NAME + '` compiler\n'
            m += 'You will need to install an appropriate compiler to build a Raspberry Pi Pico project\n'
            m += 'See the Raspberry Pi Pico documentation for how to do this on your particular platform\n'
            self.send_error(m)

        # check existence of SDK
        sdk_path = os.getenv('PICO_SDK_PATH')
        if sdk_path is None:
            m = 'Unable to locate the Raspberry Pi Pico SDK, PICO_SDK_PATH is not set'
            self.send_error(m)

        sdk_path = Path(sdk_path)
        if not sdk_path.is_dir():
            m = 'Unable to locate the Raspberry Pi Pico SDK, PICO_SDK_PATH does not point to a directory'
            self.send_error(m)
        self.build_opts['sdk_path'] = sdk_path

        # check if project name is valid
        if self.project_opts['name'] is None:
            self.send_error("No project name specfied\n")

        # check if project path is valid
        if not self.project_opts['base_path'].exists():
            self.send_error('Invalid project path. Select a valid path and try again')

    def send_error(self, msg):
        if self.parent_gui:
            self.parent_gui.RunWarning(msg)
        else:
            print(msg)
            sys.exit(-1)
