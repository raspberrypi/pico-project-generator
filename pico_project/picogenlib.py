
#
# Copyright (c) 2021 Raspberry Pi (Trading) Ltd.
#
# SPDX-License-Identifier: BSD-3-Clause
#

"""
picogenlib -- functions used for generating Pico project files to be used by the CLI or by a GUI
"""

from enum import Enum
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, pass_context
import json


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
    VSCODE = 0


class LibInfo(Enum):
    GUI_TEXT = 0
    C_FILE = 1
    H_FILE = 2
    LIB_NAME = 3


class PicoProjectFactory():
    """
    Programatically generates a Pico project. To be used as a singleton class.
    """

    def __init__(self, base_path, **kwargs):
        # options pertaining to cmake and builds
        self.build_opts = {
            "sdk_path": Path(kwargs.sdk_path),
            "wants_uart": kwargs.wants_uart,
            "wants_usb": kwargs.wants_usb,
            "run_from_ram": kwargs.run_from_ram,
            "wants_cpp": kwargs.wants_cpp,
            "exceptions": kwargs.exceptions,
            "rtti": kwargs.rtti
        }
        # options pertaining to the Pico code
        self.code_opts = {
            "features": kwargs.features,
            "wants_examples": kwargs.wants_examples
        }
        # options for Pico project generation
        self.project_opts = {
            "base_path": Path(kwargs.project_root),
            "name": kwargs.project_name,
            "wants_overwrite": kwargs.wants_overwrite,
            "wants_build": kwargs.wants_build
        }
        # options for the IDE
        self.ide_opts = {
            "name": IDE(kwargs.ide),
            "debugger": kwargs.debugger,

        }

        # pointer to Jinja env
        self.jinja_env = self._get_jinja_env(base_path / 'templates')
        self.constants = self._get_constants(base_path / 'constants.json')

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

    def _get_constants(self, path):
        with open(path, 'r') as f:
            constants = json.loads(f.read())
        return constants

    def generate_main(self):
        """
        Generates the main C/C++ file
        """
        template = self.jinja_env.get_template('main.txt')
        mapping = dict(includes=[], libraries=[])

        features_list = self.constants['features_list']
        stdlib_examples_list = self.constants['stdlib_examples_list']
        features = self.code_opts['features']

        if self.features:
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
        pass

    def generate_ide(self):
        if self.ide_opts['name'] == IDE.VSCODE:
            deb = debugger_config_list[debugger]
            vscode_path = Path(projectPath, VSCODE_FOLDER)
            if not vscode_path.is_dir():
                vscode_path.mkdir(exist_ok=True)

            args = [('vscode/launch.txt', VSCODE_LAUNCH_FILENAME, dict(deb=deb)),
                    ('vscode/c_properties.txt', VSCODE_C_PROPERTIES_FILENAME, dict()),
                    ('vscode/settings.txt', VSCODE_SETTINGS_FILENAME, dict()),
                    ('vscode/extensions.txt', VSCODE_EXTENSIONS_FILENAME, dict())]

    for template_name, file_name, mapping in args:
        template = jinja_env.get_template(template_name)
        mapping = dict(deb=deb)
        with open(projectPath / VSCODE_FOLDER / file_name, 'w') as f:
            f.write(template.render(mapping))

    def generate_all(self):
        pass
    
    def setup_project(self):
        # create project dir
        project_path = self.project_opts['base_path'] / self.project_opts['name']
        project_path.mkdir(exist_ok=True)
        self.project_opts['project_path'] = project_path


        pass
