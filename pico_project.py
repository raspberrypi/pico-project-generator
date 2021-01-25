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

def ParseCommandLine():
    parser = argparse.ArgumentParser(description='Pico Project generator')
    parser.add_argument("name", nargs="?", help="Name of the project")
    parser.add_argument("-o", "--output", help="Set an alternative CMakeList.txt filename", default="CMakeLists.txt")
    parser.add_argument("-x", "--examples", action='store_true', help="Add example code for the Pico standard library")
    parser.add_argument("-l", "--list", action='store_true', help="List available features")
    parser.add_argument("-c", "--configs", action='store_true', help="List available project configuration items")
    parser.add_argument("-f", "--feature", action='append', help="Add feature to generated project")
    parser.add_argument("-over", "--overwrite", action='store_true', help="Overwrite any existing project AND files")
    parser.add_argument("-b", "--build", action='store_true', help="Build after project created")
    parser.add_argument("-g", "--gui", action='store_true', help="Run a GUI version of the project generator")
    parser.add_argument("-p", "--project", action='append', help="Generate projects files for IDE. Options are: vscode")
    parser.add_argument("-r", "--runFromRAM", action='store_true', help="Run the program from RAM rather than flash")
    parser.add_argument("-uart", "--uart", action='store_true', default=1, help="Console output to UART (default)")
    parser.add_argument("-usb", "--usb", action='store_true', help="Console output to USB (disables other USB functionality")

    return parser.parse_args()

# Simple if command to see if the gui is requested. If it is import the gui.py file if not then don't and dont load any unecassary files.
if (ParseCommandLine().gui):
    LOAD_GUI = True
    import pico_project_gui 

def CheckPrerequisites():
    global isMac, isWindows
    isMac = (platform.system() == 'Darwin')
    isWindows = (platform.system() == 'Windows')

    # Do we have a compiler?
    return shutil.which(COMPILER_NAME)

def CheckSDKPath(gui):
    sdkPath = os.getenv('PICO_SDK_PATH')

    if sdkPath == None:
        m = 'Unabled to locate the Raspberry Pi Pico SDK, PICO_SDK_PATH is not set'
        if (gui):
            pico_project_gui.RunWarning(m)
        else:
            print(m)
    elif not os.path.isdir(sdkPath):
        m = 'Unabled to locate the Raspberry Pi Pico SDK, PICO_SDK_PATH does not point to a directory'
        if (gui):
            pico_project_gui.RunWarning(m)
        else:
            print(m)
        sdkPath = None

    return sdkPath

def LoadConfigurations():
    try:
        with open("pico_configs.tsv") as tsvfile:
            reader = csv.DictReader(tsvfile, dialect='excel-tab')
            for row in reader:
                configuration_dictionary.append(row)
    except:
        print("No Pico configurations file found. Continuing without")


###################################################################################
# main execution starteth here

args = ParseCommandLine()


# Check we have everything we need to compile etc
c = CheckPrerequisites()

## TODO Do both warnings in the same error message so user does have to keep coming back to find still more to do

if c == None:
    m = 'Unable to find the `' + COMPILER_NAME + '` compiler\n'
    m +='You will need to install an appropriate compiler to build a Raspberry Pi Pico project\n'
    m += 'See the Raspberry Pi Pico documentation for how to do this on your particular platform\n'

    if (args.gui):
        pico_project_gui.RunWarning(m)
    else:
        print(m)
    sys.exit(-1)

if args.name == None and not args.gui and not args.list and not args.configs:
    print("No project name specfied\n")
    sys.exit(-1)

# load/parse any configuration dictionary we may have
LoadConfigurations()

p = CheckSDKPath(args.gui)

if p == None:
    sys.exit(-1)

sdkPath = Path(p)

if args.gui:
    pico_project_gui.RunGUI(sdkPath, args) # does not return, only exits

projectRoot = Path(os.getcwd())

if args.list or args.configs:
    if args.list:
        print("Available project features:\n")
        for feat in features_list:
            print(feat.ljust(6), '\t', features_list[feat][GUI_TEXT])
        print('\n')

    if args.configs:
        print("Available project configuration items:\n")
        for conf in configuration_dictionary:
            print(conf['name'].ljust(40), '\t', conf['description'])
        print('\n')

    sys.exit(0)
else :
    p = Parameters(sdkPath, projectRoot, args.name, False, args.overwrite, args.build, args.feature, args.project, (), args.runFromRAM, args.examples, args.uart, args.usb)
    from pico_project_generation import DoEverything
    DoEverything(None, p)

