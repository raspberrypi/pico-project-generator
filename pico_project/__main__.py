#!/usr/bin/env python3

#
# Copyright (c) 2021 Raspberry Pi (Trading) Ltd.
#
# SPDX-License-Identifier: BSD-3-Clause
#

import cli as pico_cli
import gui as pico_gui
from picogenlib import PicoProjectFactory, LibInfo

from pathlib import Path
import os
import csv

BASE_PATH = Path(__file__).resolve().parent


def load_configs(path):
    list_to_return = []
    try:
        with open(path, 'r') as tsvfile:
            reader = csv.DictReader(tsvfile, dialect='excel-tab')
            for row in reader:
                list_to_return.append(row)
    except FileNotFoundError:
        print("No Pico configurations file found. Continuing without")


def main():
    args = pico_cli.get_args()

    # preprocess some args, these need to be refactored..
    if args['nouart']:
        args['uart'] = False

    #  TODO this could be better, need some constants etc
    if args['debugger'] > 1:
        args['debugger'] = 0

    # weeell...the user should technically be allowed to specify a path
    args['project_root'] = Path(os.getcwd())
    generator = PicoProjectFactory(BASE_PATH, args)

    features_list = generator.constants['features_list']
    # load/parse any configuration dictionary we may have
    configs = load_configs(args['tsv'])

    if args['list']:
        print("Available project features:\n")
        for feat in features_list:
            print(feat.ljust(6), '\t', features_list[feat][LibInfo.GUI_TEXT.value])
        return

    if args['configs']:
        print("Available project configuration items:\n")
        for conf in configs:
            print(conf['name'].ljust(40), '\t', conf['description'])
        return

    if args['gui']:
        pico_gui.run(generator)
    else:
        pico_cli.run(generator)


if __name__ == '__main__':
    main()
