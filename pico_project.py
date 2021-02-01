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

import tkinter as tk
from tkinter import messagebox as mb
from tkinter import filedialog as fd
from tkinter import simpledialog as sd
from tkinter import ttk

CMAKELIST_FILENAME='CMakeLists.txt'
COMPILER_NAME='arm-none-eabi-gcc'

VSCODE_LAUNCH_FILENAME = 'launch.json'
VSCODE_C_PROPERTIES_FILENAME = 'c_cpp_properties.json'
VSCODE_SETTINGS_FILENAME ='settings.json'
VSCODE_FOLDER='.vscode'

CONFIG_UNSET="Not set"

# Standard libraries for all builds
# And any more to string below, space separator
STANDARD_LIBRARIES = 'pico_stdlib'

# Indexed on feature name, tuple contains the C file, the H file and the Cmake project name for the feature
GUI_TEXT = 0
C_FILE = 1
H_FILE = 2
LIB_NAME = 3

features_list = {
    'spi' :     ("SPI",             "spi.c",            "hardware/spi.h",       "hardware_spi"),
    'i2c' :     ("I2C interface",   "i2c.c",            "hardware/i2c.h",       "hardware_i2c"),
    'dma' :     ("DMA support",     "dma.c",            "hardware/dma.h",       "hardware_dma"),
    'pio' :     ("PIO interface",   "pio.c",            "hardware/pio.h",       "hardware_pio"),
    'interp' :  ("HW interpolation", "interp.c",        "hardware/interp.h",    "hardware_interp"),
    'timer' :   ("HW timer",        "timer.c",          "hardware/timer.h",     "hardware_timer"),
    'watch' :   ("HW watchdog",     "watch.c",          "hardware/watchdog.h",  "hardware_watchdog"),
    'clocks' :  ("HW clocks",       "clocks.c",         "hardware/clocks.h",    "hardware_clocks"),
}

stdlib_examples_list = {
    'uart':     ("UART",                    "uart.c",           "hardware/uart.h",      "hardware_uart"),
    'gpio' :    ("GPIO interface",          "gpio.c",           "hardware/gpio.h",      "hardware_gpio"),
    'div' :     ("Low level HW Divider",    "divider.c",  "hardware/divider.h",   "hardware_divider")
}

DEFINES = 0
INITIALISERS = 1
# Could add an extra item that shows how to use some of the available functions for the feature
#EXAMPLE = 2

# This also contains example code for the standard library (see stdlib_examples_list)
code_fragments_per_feature = {
    'uart' : [
               ("// UART defines",
                "// By default the stdout UART is `uart0`, so we will use the second one",
                "#define UART_ID uart1",
                "#define BAUD_RATE 9600", "",
                "// Use pins 4 and 5 for UART1",
                "// Pins can be changed, see the GPIO function select table in the datasheet for information on GPIO assignments",
                "#define UART_TX_PIN 4",
                "#define UART_RX_PIN 5" ),

               ( "// Set up our UART",
                 "uart_init(UART_ID, BAUD_RATE);",
                 "// Set the TX and RX pins by using the function select on the GPIO",
                 "// Set datasheet for more information on function select",
                 "gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);",
                 "gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);", "" )
            ],
    'spi' : [
              ( "// SPI Defines",
                "// We are going to use SPI 0, and allocate it to the following GPIO pins",
                "// Pins can be changed, see the GPIO function select table in the datasheet for information on GPIO assignments",
                "#define SPI_PORT spi0",
                "#define PIN_MISO 16",
                "#define PIN_CS   17",
                "#define PIN_SCK  18",
                "#define PIN_MOSI 19" ),

              ( "// SPI initialisation. This example will use SPI at 1MHz.",
                "spi_init(SPI_PORT, 1000*1000);",
                "gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);",
                "gpio_set_function(PIN_CS,   GPIO_FUNC_SIO);",
                "gpio_set_function(PIN_SCK,  GPIO_FUNC_SPI);",
                "gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);", "",
                "// Chip select is active-low, so we'll initialise it to a driven-high state",
                "gpio_set_dir(PIN_CS, GPIO_OUT);",
                "gpio_put(PIN_CS, 1);", "")
            ],
    'i2c' : [
              (
                "// I2C defines",
                "// This example will use I2C0 on GPIO8 (SDA) and GPIO9 (SCL) running at 400KHz.",
                "// Pins can be changed, see the GPIO function select table in the datasheet for information on GPIO assignments",
                "#define I2C_PORT i2c0",
                "#define I2C_SDA 8",
                "#define I2C_SCL 9",
              ),
              (
                "// I2C Initialisation. Using it at 400Khz.",
                "i2c_init(I2C_PORT, 400*1000);","",
                "gpio_set_function(I2C_SDA, GPIO_FUNC_I2C);",
                "gpio_set_function(I2C_SCL, GPIO_FUNC_I2C);",
                "gpio_pull_up(I2C_SDA);",
                "gpio_pull_up(I2C_SCL);"
              )
            ],
    "gpio" : [
              (
                "// GPIO defines",
                "// Example uses GPIO 2",
                "#define GPIO 2"
              ),
              (
                "// GPIO initialisation.",
                "// We will make this GPIO an input, and pull it up by default",
                "gpio_init(GPIO);",
                "gpio_set_dir(GPIO, GPIO_IN);",
                "gpio_pull_up(GPIO);","",
              )
            ],
    "interp" :[
               (),
               (
                "// Interpolator example code",
                "interp_config cfg = interp_default_config();",
                "// Now use the various interpolator library functions for your use case",
                "// e.g. interp_config_clamp(&cfg, true);",
                "//      interp_config_shift(&cfg, 2);",
                "// Then set the config ",
                "interp_set_config(interp0, 0, &cfg);",
               )
              ],

    "timer"  : [
                (
                 "int64_t alarm_callback(alarm_id_t id, void *user_data) {",
                 "    // Put your timeout handler code in here",
                 "    return 0;",
                 "}"
                ),
                (
                 "// Timer example code - This example fires off the callback after 2000ms",
                 "add_alarm_in_ms(2000, alarm_callback, NULL, false);"
                )
              ],

    "watchdog":[ (),
                (
                    "// Watchdog example code",
                    "if (watchdog_caused_reboot()) {",
                    "    // Whatever action you may take if a watchdog caused a reboot",
                    "}","",
                    "// Enable the watchdog, requiring the watchdog to be updated every 100ms or the chip will reboot",
                    "// second arg is pause on debug which means the watchdog will pause when stepping through code",
                    "watchdog_enable(100, 1);","",
                    "// You need to call this function at least more often than the 100ms in the enable call to prevent a reboot"
                    "watchdog_update();",
                )
              ],

    "div"    : [ (),
                 (
                    "// Example of using the HW divider. The pico_divider library provides a more user friendly set of APIs ",
                    "// over the divider (and support for 64 bit divides), and of course by default regular C language integer",
                    "// divisions are redirected thru that library, meaning you can just use C level `/` and `%` operators and",
                    "// gain the benefits of the fast hardware divider.",
                    "int32_t dividend = 123456;",
                    "int32_t divisor = -321;",
                    "// This is the recommended signed fast divider for general use.",
                    "divmod_result_t result = hw_divider_divmod_s32(dividend, divisor);",
                    "printf(\"%d/%d = %d remainder %d\\n\", dividend, divisor, to_quotient_s32(result), to_remainder_s32(result));",
                    "// This is the recommended unsigned fast divider for general use.",
                    "int32_t udividend = 123456;",
                    "int32_t udivisor = 321;",
                    "divmod_result_t uresult = hw_divider_divmod_u32(udividend, udivisor);",
                    "printf(\"%d/%d = %d remainder %d\\n\", udividend, udivisor, to_quotient_u32(uresult), to_remainder_u32(uresult));"
                 )
                ]
}

configuration_dictionary = list(dict())

isMac = False
isWindows = False

class Parameters():
    def __init__(self, sdkPath, projectRoot, projectName, gui, overwrite, build, features, projects, configs, runFromRAM, examples, uart, usb):
        self.sdkPath = sdkPath
        self.projectRoot = projectRoot
        self.projectName = projectName
        self.wantGUI = gui
        self.wantOverwrite = overwrite
        self.wantBuild = build
        self.features = features
        self.projects = projects
        self.configs = configs
        self.wantRunFromRAM = runFromRAM
        self.wantExamples = examples
        self.wantUART = uart
        self.wantUSB = usb

def GetBackground():
    return 'white'

def GetButtonBackground():
    return 'white'

def GetTextColour():
    return 'black'

def GetButtonTextColour():
    return '#c51a4a'

def RunGUI(sdkpath, args):
    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use('default')

    ttk.Style().configure("TButton", padding=6, relief="groove", border=2, foreground=GetButtonTextColour(), background=GetButtonBackground())
    ttk.Style().configure("TLabel", foreground=GetTextColour(), background=GetBackground() )
    ttk.Style().configure("TCheckbutton", foreground=GetTextColour(), background=GetBackground() )
    ttk.Style().configure("TRadiobutton", foreground=GetTextColour(), background=GetBackground() )
    ttk.Style().configure("TLabelframe", foreground=GetTextColour(), background=GetBackground() )
    ttk.Style().configure("TLabelframe.Label", foreground=GetTextColour(), background=GetBackground() )

    app = ProjectWindow(root, sdkpath, args)

    app.configure(background=GetBackground())

    root.mainloop()
    sys.exit(0)

def RunWarning(message):
    mb.showwarning('Raspberry Pi Pico Project Generator', message)
    sys.exit(0)


class ChecklistBox(tk.Frame):
    def __init__(self, parent, entries):
        tk.Frame.__init__(self, parent)

        self.vars = []
        for c in entries:
            # This var will be automatically updated by the checkbox
            # The checkbox fills the var with the "onvalue" and "offvalue" as
            # it is clicked on and off
            var = tk.StringVar(value='') # Off by default for the moment
            self.vars.append(var)
            cb = ttk.Checkbutton(self, var=var, text=c,
                                onvalue=c, offvalue="",
                                width=20)
            cb.pack(side="top", fill="x", anchor="w")

    def getCheckedItems(self):
        values = []
        for var in self.vars:
            value =  var.get()
            if value:
                values.append(value)
        return values


import threading

def thread_function(text, command, ok):
    l = shlex.split(command)
    proc = subprocess.Popen(l, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(proc.stdout.readline,''):
        if not line:
            if ok:
                ok["state"] = tk.NORMAL
            return
        text.insert(tk.END, line)
        text.see(tk.END)

# Function to run an OS command and display the output in a new modal window
class DisplayWindow(tk.Toplevel):
    def __init__(self, parent, title):
        tk.Toplevel.__init__(self, parent)
        self.parent = parent
        self.init_window(title)

    def init_window(self, title):
        self.title(title)

        frame = tk.Frame(self, borderwidth=5, relief=tk.RIDGE)
        frame.pack(fill=tk.X, expand=True, side=tk.TOP)

        scrollbar = tk.Scrollbar(frame)
        self.text = tk.Text(frame, bg='gray14', fg='gray99')
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.Y)
        scrollbar.config(command=self.text.yview)
        self.text.config(yscrollcommand=scrollbar.set)

        frame1 = tk.Frame(self, borderwidth=1)
        frame1.pack(fill=tk.X, expand=True, side=tk.BOTTOM)
        self.OKButton = ttk.Button(frame1, text="OK", command=self.OK)
        self.OKButton["state"] = tk.DISABLED
        self.OKButton.pack()

        # make dialog modal
        self.transient(self.parent)
        self.grab_set()

    def OK(self):
        self.destroy()

def RunCommandInWindow(parent, command):
    w = DisplayWindow(parent, command)
    x = threading.Thread(target=thread_function, args=(w.text, command, w.OKButton))
    x.start()
    parent.wait_window(w)

class EditBoolWindow(sd.Dialog):

    def __init__(self, parent, configitem, current):
        self.parent = parent
        self.config_item = configitem
        self.current = current
        sd.Dialog.__init__(self, parent, "Edit boolean configuration")


    def body(self, master):
        self.configure(background=GetBackground())
        ttk.Label(self, text=self.config_item['name']).pack()
        self.result = tk.StringVar()
        self.result.set(self.current)
        ttk.Radiobutton(master, text="True", variable=self.result, value="True").pack(anchor=tk.W)
        ttk.Radiobutton(master, text="False", variable=self.result, value="False").pack(anchor=tk.W)
        ttk.Radiobutton(master, text=CONFIG_UNSET, variable=self.result, value=CONFIG_UNSET).pack(anchor=tk.W)

    def get(self):
        return self.result.get()

class EditIntWindow(sd.Dialog):

    def __init__(self, parent, configitem, current):
        self.parent = parent
        self.config_item = configitem
        self.current = current
        sd.Dialog.__init__(self, parent, "Edit integer configuration")

    def body(self, master):
        self.configure(background=GetBackground())
        str = self.config_item['name'] + "  Max = " + self.config_item['max'] + "  Min = " + self.config_item['min']
        ttk.Label(self, text=str).pack()
        self.input =  tk.Entry(self)
        self.input.pack(pady=4)
        self.input.insert(0, self.current)
        ttk.Button(self, text=CONFIG_UNSET, command=self.unset).pack(pady=5)

    def validate(self):
        self.result = self.input.get()
        # Check for numeric entry
        return True

    def unset(self):
        self.result = CONFIG_UNSET
        self.destroy()

    def get(self):
        return self.result

class EditEnumWindow(sd.Dialog):
    def __init__(self, parent, configitem, current):
        self.parent = parent
        self.config_item = configitem
        self.current = current
        sd.Dialog.__init__(self, parent, "Edit Enumeration configuration")

    def body(self, master):
        #self.configure(background=GetBackground())
        values = self.config_item['enumvalues'].split('|')
        values.insert(0,'Not set')
        self.input =  ttk.Combobox(self, values=values, state='readonly')
        self.input.set(self.current)
        self.input.pack(pady=12)

    def validate(self):
        self.result = self.input.get()
        return True

    def get(self):
        return self.result


class ConfigurationWindow(tk.Toplevel):

    def __init__(self, parent, initial_config):
        tk.Toplevel.__init__(self, parent)
        self.master = parent
        self.results = initial_config
        self.init_window(self)

    def init_window(self, args):
        self.configure(background=GetBackground())
        self.title("Advanced Configuration")
        ttk.Label(self, text="Select the advanced options you wish to enable or change. Note that you really should understand the implications of changing these items before using them!").grid(row=0, column=0, columnspan=5)
        ttk.Label(self, text="Name").grid(row=1, column=0, sticky=tk.W)
        ttk.Label(self, text="Type").grid(row=1, column=1, sticky=tk.W)
        ttk.Label(self, text="Min").grid(row=1, column=2, sticky=tk.W)
        ttk.Label(self, text="Max").grid(row=1, column=3, sticky=tk.W)
        ttk.Label(self, text="Default").grid(row=1, column=4, sticky=tk.W)
        ttk.Label(self, text="User").grid(row=1, column=5, sticky=tk.W)

        okButton = ttk.Button(self, text="OK", command=self.ok)
        cancelButton = ttk.Button(self, text="Cancel", command=self.cancel)

        self.namelist = tk.Listbox(self, selectmode=tk.SINGLE)
        self.typelist = tk.Listbox(self, selectmode=tk.SINGLE)
        self.minlist = tk.Listbox(self, selectmode=tk.SINGLE)
        self.maxlist = tk.Listbox(self, selectmode=tk.SINGLE)
        self.defaultlist = tk.Listbox(self, selectmode=tk.SINGLE)
        self.valuelist = tk.Listbox(self, selectmode=tk.SINGLE)

        self.descriptionText = tk.Text(self, state=tk.DISABLED, height=2)

        ## Make a list of our list boxes to make it all easier to handle
        self.listlist = [self.namelist, self.typelist, self.minlist, self.maxlist, self.defaultlist, self.valuelist]

        scroll = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.yview)

        for box in self.listlist:
            box.config(width=0)
            box.config(yscrollcommand=scroll.set)
            box.bind("<MouseWheel>", self.mousewheel)
            box.bind("<Button-4>", self.mousewheel)
            box.bind("<Button-5>", self.mousewheel)
            box.bind("<<ListboxSelect>>", self.changeSelection)
            box.bind("<Double-Button>", self.doubleClick)
            box.config(exportselection=False)
            box.bind("<Down>", self.OnEntryUpDown)
            box.bind("<Up>", self.OnEntryUpDown)

        scroll.grid(column=7, sticky=tk.N + tk.S)

        i = 0
        for box in self.listlist:
            box.grid(row=2, column=i, padx=0, sticky=tk.W + tk.E)
            i+=1

        self.descriptionText.grid(row = 3, column=0, columnspan=4, sticky=tk.W + tk.E)
        cancelButton.grid(column=4, row = 3, sticky=tk.E, padx=5)
        okButton.grid(column=5, row = 3, padx=5)

        # populate the list box with our config options
        for conf in configuration_dictionary:
            self.namelist.insert(tk.END, conf['name'])
            s = conf['type']
            if s == "":
                s = "int"
            self.typelist.insert(tk.END, s)
            self.maxlist.insert(tk.END, conf['max'])
            self.minlist.insert(tk.END, conf['min'])
            self.defaultlist.insert(tk.END, conf['default'])

            # see if this config has a setting, our results member has this predefined from init
            val = self.results.get(conf['name'], CONFIG_UNSET)
            self.valuelist.insert(tk.END, val)
            if val != CONFIG_UNSET:
                self.valuelist.itemconfig(self.valuelist.size() - 1, {'bg':'green'})

    def yview(self, *args):
        for box in self.listlist:
            box.yview(*args)

    def mousewheel(self, event):
        if (event.num == 4):    # Linux encodes wheel as 'buttons' 4 and 5
            delta = -1
        elif (event.num == 5):
            delta = 1
        else:                   # Windows & OSX
            delta = event.delta

        for box in self.listlist:
            box.yview("scroll", delta, "units")
        return "break"

    def changeSelection(self, evt):
        box = evt.widget
        sellist = box.curselection()

        if sellist:
            index = int(sellist[0])
            config = self.namelist.get(index)
            # Now find the description for that config in the dictionary
            for conf in configuration_dictionary:
                if conf['name'] == config:
                    self.descriptionText.config(state=tk.NORMAL)
                    self.descriptionText.delete(1.0,tk.END)
                    str = config + "\n" + conf['description']
                    self.descriptionText.insert(1.0, str)
                    self.descriptionText.config(state=tk.DISABLED)
                    break
            # Set all the other list boxes to the same index
            for b in self.listlist:
                if b != box:
                    b.selection_clear(0, tk.END)
                    b.selection_set(index)

    def OnEntryUpDown(self, event):
        box = event.widget
        selection = box.curselection()

        if selection:
            index = int(selection[0])
            if event.keysym == 'Up':
                index -= 1
            elif event.keysym == 'Down':
                index += 1

            if 0 <= index < box.size():
                for b in self.listlist:
                        b.selection_clear(0, tk.END)
                        b.selection_set(index)
                        b.see(index)

    def doubleClick(self, evt):
        box = evt.widget
        index = int(box.curselection()[0])
        config = self.namelist.get(index)
        # Get the associated dict entry from our list of configs
        for conf in configuration_dictionary:
            if conf['name'] == config:
                if (conf['type'] == 'bool'):
                    result = EditBoolWindow(self, conf, self.valuelist.get(index)).get()
                elif (conf['type'] == 'int' or conf['type'] == ""): # "" defaults to int
                    result = EditIntWindow(self, conf, self.valuelist.get(index)).get()
                elif conf['type'] == 'enum':
                    result = EditEnumWindow(self, conf, self.valuelist.get(index)).get()

                # Update the valuelist with our new item
                self.valuelist.delete(index)
                self.valuelist.insert(index, result)
                if result != CONFIG_UNSET:
                    self.valuelist.itemconfig(index, {'bg':'green'})
                break

    def ok(self):
        # Get the selections, and create a list of them
        for i, val in enumerate(self.valuelist.get(0, tk.END)):
            if val != CONFIG_UNSET:
                self.results[self.namelist.get(i)] = val

        self.destroy()

    def cancel(self):
        self.destroy()

    def get(self):
        return self.results


# Our main window
class ProjectWindow(tk.Frame):

    def __init__(self, parent, sdkpath, args):
        tk.Frame.__init__(self, parent)
        self.master = parent
        self.sdkpath = sdkpath
        self.init_window(args)
        self.configs = dict()

    def init_window(self, args):
        self.master.title("Raspberry Pi Pico Project Generator")
        self.master.configure(bg=GetBackground())

        mainFrame = tk.Frame(self, bg=GetBackground()).grid(row=0, column=0, columnspan=6, rowspan=12)

        # Need to keep a reference to the image or it will not appear.
        self.logo = tk.PhotoImage(file=self._get_filepath("logo_alpha.gif"))
        logowidget = ttk.Label(mainFrame, image=self.logo, borderwidth=0, relief="solid").grid(row=0,column=0, columnspan=5, pady=10)

        namelbl = ttk.Label(mainFrame, text='Project Name :').grid(row=2, column=0, sticky=tk.E)
        self.projectName = tk.StringVar()

        if args.name != None:
            self.projectName.set(args.name)
        else:
            self.projectName.set('ProjectName')

        nameEntry = ttk.Entry(mainFrame, textvariable=self.projectName).grid(row=2, column=1, sticky=tk.W+tk.E, padx=5)

        locationlbl = ttk.Label(mainFrame, text='Location :').grid(row=3, column=0, sticky=tk.E)
        self.locationName = tk.StringVar()
        self.locationName.set(os.getcwd())
        locationEntry = ttk.Entry(mainFrame, textvariable=self.locationName).grid(row=3, column=1, columnspan=3, sticky=tk.W+tk.E, padx=5)
        locationBrowse = ttk.Button(mainFrame, text='Browse', command=self.browse).grid(row=3, column=4)

        # Features section
        featuresframe = ttk.LabelFrame(mainFrame, text="Library Options", relief=tk.RIDGE, borderwidth=2)
        featuresframe.grid(row=4, column=0, columnspan=5, rowspan=5, ipadx=5, padx=5, sticky=tk.E+tk.W)

        # Add features to the list
        v = []
        for i in features_list:
            v.append(features_list[i][GUI_TEXT])

        s = (len(v)//3) + 1

        self.featuresEntry0 = ChecklistBox(featuresframe, v[:s])
        self.featuresEntry0.grid(row=5, column=1, padx=4)
        self.featuresEntry1 = ChecklistBox(featuresframe, v[s:s+s])
        self.featuresEntry1.grid(row=5, column=2, padx=4)
        self.featuresEntry2 = ChecklistBox(featuresframe, v[s+s:])
        self.featuresEntry2.grid(row=5, column=3, padx=4)

        optionsRow = 9

        # output options section
        ooptionsSubframe = ttk.LabelFrame(mainFrame, relief=tk.RIDGE, borderwidth=2, text="Console Options")
        ooptionsSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=2, padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)

        self.wantUART = tk.IntVar()
        self.wantUART.set(args.uart)
        ttk.Checkbutton(ooptionsSubframe, text="Console over UART", variable=self.wantUART).grid(row=0, column=0, padx=4, sticky=tk.W)

        self.wantUSB = tk.IntVar()
        self.wantUSB.set(args.usb)
        ttk.Checkbutton(ooptionsSubframe, text="Console over USB (Disables other USB use)", variable=self.wantUSB).grid(row=0, column=1, padx=4, sticky=tk.W)

        optionsRow += 2

        # Code options section
        coptionsSubframe = ttk.LabelFrame(mainFrame, relief=tk.RIDGE, borderwidth=2, text="Code Options")
        coptionsSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=2, padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)

        self.wantExamples = tk.IntVar()
        self.wantExamples.set(args.examples)
        ttk.Checkbutton(coptionsSubframe, text="Add examples for Pico library", variable=self.wantExamples).grid(row=0, column=0, padx=4, sticky=tk.W)

        self.wantRunFromRAM = tk.IntVar()
        self.wantRunFromRAM.set(args.runFromRAM)
        ttk.Checkbutton(coptionsSubframe, text="Run from RAM", variable=self.wantRunFromRAM).grid(row=0, column=1, padx=4, sticky=tk.W)

        ttk.Button(coptionsSubframe, text="Advanced...", command=self.config).grid(row=0, column=4, sticky=tk.E)

        optionsRow += 2

        # Build Options section

        boptionsSubframe = ttk.LabelFrame(mainFrame, relief=tk.RIDGE, borderwidth=2, text="Build Options")
        boptionsSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=2, padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)

        self.wantBuild = tk.IntVar()
        self.wantBuild.set(args.build)
        ttk.Checkbutton(boptionsSubframe, text="Run build", variable=self.wantBuild).grid(row=0, column=0, padx=4, sticky=tk.W)

        self.wantOverwrite = tk.IntVar()
        self.wantOverwrite.set(args.overwrite)
        ttk.Checkbutton(boptionsSubframe, text="Overwrite project", variable=self.wantOverwrite).grid(row=0, column=1, padx=4, sticky=tk.W)

        self.wantVSCode = tk.IntVar()
        ttk.Checkbutton(boptionsSubframe, text="Create VSCode project", variable=self.wantVSCode).grid(row=0, column=2, padx=4, sticky=tk.W)

        optionsRow += 2

        # OK, Cancel, Help section
        # creating buttons
        QuitButton = ttk.Button(mainFrame, text="Quit", command=self.quit).grid(row=optionsRow, column=3, padx=4, pady=5, sticky=tk.E)
        OKButton = ttk.Button(mainFrame, text="OK", command=self.OK).grid(row=optionsRow, column=4, stick=tk.E, padx=10, pady=5)
        # TODO help not implemented yet
        # HelpButton = ttk.Button(mainFrame, text="Help", command=self.help).grid(row=optionsRow, column=0, pady=5)

        # You can set a default path here, replace the string with whereever you want.
        # self.locationName.set('/home/pi/pico_projects')

    def GetFeatures(self):
        features = []

        f = self.featuresEntry0.getCheckedItems()
        f += self.featuresEntry1.getCheckedItems()
        f += self.featuresEntry2.getCheckedItems()

        for feat in features_list:
            if features_list[feat][GUI_TEXT] in f :
                features.append(feat)

        return features

    def quit(self):
        # TODO Check if we want to exit here
        sys.exit(0)

    def OK(self):
        # OK, grab all the settings from the page, then call the generators
        projectPath = self.locationName.get()
        features = self.GetFeatures()
        projects = list()
        if (self.wantVSCode):
            projects.append("vscode")

        p = Parameters(self.sdkpath, Path(projectPath), self.projectName.get(), True, self.wantOverwrite.get(), self.wantBuild.get(),\
                       features, projects, self.configs, self.wantRunFromRAM.get(), \
                       self.wantExamples.get(),\
                       self.wantUSB.get(), self.wantUART.get())

        DoEverything(self, p)

    def browse(self):
        name = fd.askdirectory()
        self.locationName.set(name)

    def help(self):
        print("Help TODO")

    def config(self):
        # Run the configuration window
        self.configs = ConfigurationWindow(self, self.configs).get()

    def _get_filepath(self, filename):
        return os.path.join(os.path.dirname(__file__), filename)

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
            RunWarning(m)
        else:
            print(m)
    elif not os.path.isdir(sdkPath):
        m = 'Unabled to locate the Raspberry Pi Pico SDK, PICO_SDK_PATH does not point to a directory'
        if (gui):
            RunWarning(m)
        else:
            print(m)
        sdkPath = None

    return sdkPath


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


def GenerateCMake(folder, params):

    cmake_header1 = ("# Generated Cmake Pico project file\n\n"
                 "cmake_minimum_required(VERSION 3.12)\n\n"
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


def LoadConfigurations():
    try:
        with open("pico_configs.tsv") as tsvfile:
            reader = csv.DictReader(tsvfile, dialect='excel-tab')
            for row in reader:
                configuration_dictionary.append(row)
    except:
        print("No Pico configurations file found. Continuing without")

def DoEverything(parent, params):

    if not os.path.exists(params.projectRoot):
        if params.wantGUI:
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
        RunCommandInWindow(parent, cmakeCmd)
    else:
        os.system(cmakeCmd)

    if params.projects:
        generateProjectFiles(projectPath, params.projectName, params.sdkPath, params.projects)

    if params.wantBuild:
        if params.wantGUI:
            RunCommandInWindow(parent, makeCmd)
        else:
            os.system(makeCmd)
            print('\nIf the application has built correctly, you can now transfer it to the Raspberry Pi Pico board')

    os.chdir(oldCWD)


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
        RunWarning(m)
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
    RunGUI(sdkPath, args) # does not return, only exits

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

    DoEverything(None, p)

