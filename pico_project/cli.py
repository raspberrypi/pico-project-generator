#
# Copyright (c) 2021 Raspberry Pi (Trading) Ltd.
#
# SPDX-License-Identifier: BSD-3-Clause
#

"""
cli -- configuration for the pico-project-generator command line interface
"""

import argparse
from picogenlib import PicoProjectFactory

def get_args():
    parser = argparse.ArgumentParser(description='Raspberry Pi Pico Project Generator')
    parser.add_argument("name", nargs="?", help="Name of the project")
    parser.add_argument("-t", "--tsv", help="Select an alternative pico_configs.tsv file", default="pico_configs.tsv")
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
    parser.add_argument("-nouart", "--nouart", action='store_true', default=0, help="Disable console output to UART")
    parser.add_argument("-usb", "--usb", action='store_true',
                        help="Console output to USB (disables other USB functionality")
    parser.add_argument("-cpp", "--cpp", action='store_true', default=0, help="Generate C++ code")
    parser.add_argument("-cpprtti", "--cpprtti", action='store_true',
                        default=0, help="Enable C++ RTTI (Uses more memory)")
    parser.add_argument("-cppex", "--cppexceptions", action='store_true',
                        default=0, help="Enable C++ exceptions (Uses more memory)")
    parser.add_argument("-d", "--debugger", type=int, help="Select debugger (0 = SWD, 1 = PicoProbe)", default=0)

    return vars(parser.parse_args()).copy()

def run(generator: PicoProjectFactory):
    """
    run function for the CLI frontend
    """
    generator.verify_build_system()
    generator.setup_project()
    generator.setup_build_system()
    generator.generate_all()
    generator.run_cmake()
    return
