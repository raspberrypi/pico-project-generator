#!/usr/bin/env python3

#
# Copyright (c) 2020 Raspberry Pi (Trading) Ltd.
#
# SPDX-License-Identifier: BSD-3-Clause
#

import argparse
import os
import shutil
from pathlib import Path
import sys
import subprocess
from time import sleep
import platform
import shlex
import csv

from pico_project_settings import *

def DoEverything(parent, params):

    if not os.path.exists(params.projectRoot):
        if params.wantGUI:
            from tkinter import messagebox as mb
            mb.showerror('Raspberry Pi Pico Project Generator', 'Invalid project path. Select a valid path and try again')
            return
        else:
            print('Invalid project path')
            sys.exit(-1)

    oldCWD = os.getcwd()
    os.chdir(params.projectRoot)

    # Create our project folder as subfolder
    os.makedirs(params.projectName, exist_ok=True)

    os.chdir(params.projectName)

    projectPath = params.projectRoot / params.projectName

    # First check if there is already a project in the folder
    # If there is we abort unless the overwrite flag it set
    if os.path.exists(CMAKELIST_FILENAME):
        if not params.wantOverwrite :
            if params.wantGUI:
                # We can ask the user if they want to overwrite
                from tkinter import messagebox as mb
                y = mb.askquestion('Raspberry Pi Pico Project Generator', 'There already appears to be a project in this folder. \nPress Yes to overwrite project files, or Cancel to chose another folder')
                if y != 'yes':
                    return
            else:
                print('There already appears to be a project in this folder. Use the --overwrite option to overwrite the existing project')
                sys.exit(-1)

        # We should really confirm the user wants to overwrite
        #print('Are you sure you want to overwrite the existing project files? (y/N)')
        #c = input().split(" ")[0]
        #if c != 'y' and c != 'Y' :
        #    sys.exit(0)

    # Copy the SDK finder cmake file to our project folder
    # Can be found here <PICO_SDK_PATH>/external/pico_sdk_import.cmake
    shutil.copyfile(params.sdkPath / 'external' / 'pico_sdk_import.cmake', projectPath / 'pico_sdk_import.cmake' )

    if params.features:
        features_and_examples = params.features[:]
    else:
        features_and_examples= []

    if params.wantExamples:
        features_and_examples = list(stdlib_examples_list.keys()) + features_and_examples

    GenerateMain('.', params.projectName, features_and_examples)

    GenerateCMake('.', params)

    # Create a build folder, and run our cmake project build from it
    if not os.path.exists('build'):
        os.mkdir('build')

    os.chdir('build')

    cpus = os.cpu_count()
    if cpus == None:
        cpus = 1

    if isWindows:
        cmakeCmd = 'cmake -DCMAKE_BUILD_TYPE=Debug -G "NMake Makefiles" ..'
        makeCmd = 'nmake -j ' + str(cpus)
    else:
        cmakeCmd = 'cmake -DCMAKE_BUILD_TYPE=Debug ..'
        makeCmd = 'make -j' + str(cpus)

    if params.wantGUI:
        from pico_project_gui import RunCommandInWindow
        RunCommandInWindow(parent, cmakeCmd)
    else:
        os.system(cmakeCmd)

    if params.projects:
        generateProjectFiles(projectPath, params.projectName, params.sdkPath, params.projects)

    if params.wantBuild:
        if params.wantGUI:
            from pico_project_gui import RunCommandInWindow
            RunCommandInWindow(parent, makeCmd)
        else:
            os.system(makeCmd)
            print('\nIf the application has built correctly, you can now transfer it to the Raspberry Pi Pico board')

    os.chdir(oldCWD)

def GenerateMain(folder, projectName, features):

    filename = Path(folder) / (projectName + '.c')

    file = open(filename, 'w')

    main = ('#include <stdio.h>\n'
            '#include "pico/stdlib.h"\n'
            )
    file.write(main)

    if (features):

        # Add any includes
        for feat in features:
            if (feat in features_list):
                o = '#include "' +  features_list[feat][H_FILE] + '"\n'
                file.write(o)
            if (feat in stdlib_examples_list):
                o = '#include "' +  stdlib_examples_list[feat][H_FILE] + '"\n'
                file.write(o)

        file.write('\n')

        # Add any defines
        for feat in features:
            if (feat in code_fragments_per_feature):
                for s in code_fragments_per_feature[feat][DEFINES]:
                    file.write(s)
                    file.write('\n')
                file.write('\n')

    main = ('\n\n'
            'int main()\n'
            '{\n'
            '    stdio_init_all();\n\n'
            )

    if (features):
        # Add any initialisers
        indent = 4
        for feat in features:
            if (feat in code_fragments_per_feature):
                for s in code_fragments_per_feature[feat][INITIALISERS]:
                    main += (" " * indent)
                    main += s
                    main += '\n'
            main += '\n'

    main += ('    puts("Hello, world!");\n\n'
             '    return 0;\n'
             '}\n'
            )

    file.write(main)

    file.close()

# Generates the requested project files, if any
def generateProjectFiles(projectPath, projectName, sdkPath, projects):

    oldCWD = os.getcwd()

    os.chdir(projectPath)

    for p in projects :
        if p == 'vscode':
            v1 = ('{\n'
                  '  // Use IntelliSense to learn about possible attributes.\n'
                  '  // Hover to view descriptions of existing attributes.\n'
                  '  // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387\n'
                  '  "version": "0.2.0",\n'
                  '  "configurations": [\n'
                  '    {\n'
                  '      "name": "Cortex Debug",\n'
                  '      "cwd": "${workspaceRoot}",\n'
                  '      "executable": "${workspaceRoot}/build/' + projectName + '.elf",\n'
                  '      "request": "launch",\n'
                  '      "type": "cortex-debug",\n'
                  '      "servertype": "openocd",\n'
                  '      "device": "Pico2040",\n'
                  '      "configFiles": [\n' + \
                  '        "interface/raspberrypi-swd.cfg",\n' + \
                  '        "target/rp2040.cfg"\n' + \
                  '        ],\n' +  \
                  '      "svdFile": "' + str(sdkPath) + '/src/rp2040/hardware_regs/rp2040.svd",\n'
                  '      "runToMain": true,\n'
                  '    }\n'
                  '  ]\n'
                  '}\n')

            c1 = ('{\n'
                  '  "configurations": [\n'
                  '    {\n'
                  '      "name": "Linux",\n'
                  '      "includePath": [\n'
                  '        "${workspaceFolder}/**",\n'
                  '        "${env:PICO_SDK_PATH}/**"\n'
                  '      ],\n'
                  '      "defines": [],\n'
                  '      "compilerPath": "/usr/bin/arm-none-eabi-gcc",\n'
                  '      "cStandard": "gnu17",\n'
                  '      "cppStandard": "gnu++14",\n'
                  '      "intelliSenseMode": "gcc-arm"\n'
                  '    }\n'
                  '  ],\n'
                  '  "version": 4\n'
                  '}\n')

            s1 = ( '{\n'
                   '  "cmake.configureOnOpen": false,\n'
                   '  "cmake.statusbar.advanced": {\n'
                   '    "debug" : {\n'
                   '      "visibility": "hidden"\n'
                   '              },'
                   '    "launch" : {\n'
                   '      "visibility": "hidden"\n'
                   '               },\n'
                   '    "build" : {\n'
                   '      "visibility": "hidden"\n'
                   '               },\n'
                   '    "buildTarget" : {\n'
                   '      "visibility": "hidden"\n'
                   '               },\n'
                   '     },\n'
                   '}\n')

            # Create a build folder, and run our cmake project build from it
            if not os.path.exists(VSCODE_FOLDER):
                os.mkdir(VSCODE_FOLDER)

            os.chdir(VSCODE_FOLDER)

            filename = VSCODE_LAUNCH_FILENAME
            file = open(filename, 'w')
            file.write(v1)
            file.close()

            file = open(VSCODE_C_PROPERTIES_FILENAME, 'w')
            file.write(c1)
            file.close()

            file = open(VSCODE_SETTINGS_FILENAME, 'w')
            file.write(s1)
            file.close()

        else :
            print('Unknown project type requested')

    os.chdir(oldCWD)

def GenerateCMake(folder, params):

    cmake_header1 = ("# Generated Cmake Pico project file\n\n"
                 "cmake_minimum_required(VERSION 3.13)\n\n"
                 "set(CMAKE_C_STANDARD 11)\n"
                 "set(CMAKE_CXX_STANDARD 17)\n\n"
                 "# initalize pico_sdk from installed location\n"
                 "# (note this can come from environment, CMake cache etc)\n"
                )

    cmake_header2 = ("# Pull in Pico SDK (must be before project)\n"
                "include(pico_sdk_import.cmake)\n\n"
                )

    cmake_header3 = (
                "# Initialise the Pico SDK\n"
                "pico_sdk_init()\n\n"
                "# Add executable. Default name is the project name, version 0.1\n\n"
                )


    filename = Path(folder) / CMAKELIST_FILENAME

    file = open(filename, 'w')

    file.write(cmake_header1)

    # OK, for the path, CMake will accept forward slashes on Windows, and thats
    # seemingly a bit easier to handle than the backslashes

    p = str(params.sdkPath).replace('\\','/')
    p = '\"' + p + '\"'

    file.write('set(PICO_SDK_PATH ' + p + ')\n\n')
    file.write(cmake_header2)
    file.write('project(' + params.projectName + ' C CXX)\n\n')
    file.write(cmake_header3)

    # add the preprocessor defines for overall configuration
    if params.configs:
        file.write('# Add any PICO_CONFIG entries specified in the Advanced settings\n')
        for c, v in params.configs.items():
            file.write('add_compile_definitions(-D' + c + '=' + v + ')\n')
        file.write('\n')

    # No GUI/command line to set a different executable name at this stage
    executableName = params.projectName

    file.write('add_executable(' + params.projectName + ' ' + params.projectName + '.c )\n\n')
    file.write('pico_set_program_name(' + params.projectName + ' "' + executableName + '")\n')
    file.write('pico_set_program_version(' + params.projectName + ' "0.1")\n\n')

    if params.wantRunFromRAM:
        file.write('# no_flash means the target is to run from RAM\n')
        file.write('pico_set_binary_type(' + params.projectName + ' no_flash)\n\n')

    # Console output destinations
    if params.wantUART:
        file.write('pico_enable_stdio_uart(' + params.projectName + ' 1)\n')
    else:
        file.write('pico_enable_stdio_uart(' + params.projectName + ' 0)\n')

    if params.wantUSB:
        file.write('pico_enable_stdio_usb(' + params.projectName + ' 1)\n\n')
    else:
        file.write('pico_enable_stdio_usb(' + params.projectName + ' 0)\n\n')

    # Standard libraries
    file.write('# Add the standard library to the build\n')
    file.write('target_link_libraries(' + params.projectName + ' ' + STANDARD_LIBRARIES + ')\n\n')


    # Selected libraries/features
    if (params.features):
        file.write('# Add any user requested libraries\n')
        file.write('target_link_libraries(' + params.projectName + '\n')
        for feat in params.features:
            if (feat in features_list):
                file.write("        " + features_list[feat][LIB_NAME] + '\n')
        file.write('        )\n\n')

    file.write('pico_add_extra_outputs(' + params.projectName + ')\n\n')

    file.close()
