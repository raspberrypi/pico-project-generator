#!/usr/bin/env python3

#
# Copyright (c) 2020 Raspberry Pi (Trading) Ltd.
#
# SPDX-License-Identifier: BSD-3-Clause
#

import argparse
from copy import copy
import os
from pyexpat import features
import shutil
from pathlib import Path
import string
import sys
import subprocess
import platform
import shlex
import csv

import tkinter as tk
from tkinter import messagebox as mb
from tkinter import filedialog as fd
from tkinter import simpledialog as sd
from tkinter import ttk

CMAKELIST_FILENAME = 'CMakeLists.txt'
CMAKECACHE_FILENAME = 'CMakeCache.txt'

COMPILER_NAME = 'arm-none-eabi-gcc'

VSCODE_LAUNCH_FILENAME = 'launch.json'
VSCODE_C_PROPERTIES_FILENAME = 'c_cpp_properties.json'
VSCODE_SETTINGS_FILENAME ='settings.json'
VSCODE_EXTENSIONS_FILENAME ='extensions.json'
VSCODE_FOLDER='.vscode'

CONFIG_UNSET="Not set"

# Standard libraries for all builds
# And any more to string below, space separator
STANDARD_LIBRARIES = 'pico_stdlib'

# Indexed on feature name, tuple contains the C file, the H file and the CMake project name for the feature. 
# Some lists may contain an extra/ancillary file needed for that feature
GUI_TEXT = 0
C_FILE = 1
H_FILE = 2
LIB_NAME = 3
ANCILLARY_FILE = 4

features_list = {
    'spi' :             ("SPI",             "spi.c",            "hardware/spi.h",       "hardware_spi"),
    'i2c' :             ("I2C interface",   "i2c.c",            "hardware/i2c.h",       "hardware_i2c"),
    'dma' :             ("DMA support",     "dma.c",            "hardware/dma.h",       "hardware_dma"),
    'pio' :             ("PIO interface",   "pio.c",            "hardware/pio.h",       "hardware_pio"),
    'interp' :          ("HW interpolation", "interp.c",        "hardware/interp.h",    "hardware_interp"),
    'timer' :           ("HW timer",        "timer.c",          "hardware/timer.h",     "hardware_timer"),
    'watchdog' :        ("HW watchdog",     "watch.c",          "hardware/watchdog.h",  "hardware_watchdog"),
    'clocks' :          ("HW clocks",       "clocks.c",         "hardware/clocks.h",    "hardware_clocks"),
}

picow_options_list = {
    'picow_none' :      ("None", "",                            "",    "",                                                                  ""),
    'picow_led' :       ("PicoW onboard LED", "",               "pico/cyw43_arch.h",    "pico_cyw43_arch_none",                             ""),
    'picow_poll' :      ("Polled lwIP",     "",                 "pico/cyw43_arch.h",    "pico_cyw43_arch_lwip_poll",                        "lwipopts.h"),
    'picow_background' :("Background lwIP", "",                 "pico/cyw43_arch.h",    "pico_cyw43_arch_lwip_threadsafe_background",       "lwipopts.h"),
#    'picow_freertos' :  ("Full lwIP (FreeRTOS)", "",            "pico/cyw43_arch.h",    "pico_cyw43_arch_lwip_sys_freertos",                "lwipopts.h"),
}

stdlib_examples_list = {
    'uart':     ("UART",                    "uart.c",           "hardware/uart.h",      "hardware_uart"),
    'gpio' :    ("GPIO interface",          "gpio.c",           "hardware/gpio.h",      "hardware_gpio"),
    'div' :     ("Low level HW Divider",    "divider.c",        "hardware/divider.h",   "hardware_divider")
}

debugger_list = ["DebugProbe (CMSIS-DAP)", "SWD (Pi host)"]
debugger_config_list = ["cmsis-dap.cfg", "raspberrypi-swd.cfg"]

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
compilerPath = Path("/usr/bin/arm-none-eabi-gcc")

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

    style.configure("TButton", padding=6, relief="groove", border=2, foreground=GetButtonTextColour(), background=GetButtonBackground())
    style.configure("TLabel", foreground=GetTextColour(), background=GetBackground() )
    style.configure("TCheckbutton", foreground=GetTextColour(), background=GetBackground())
    style.configure("TRadiobutton", foreground=GetTextColour(), background=GetBackground() )
    style.configure("TLabelframe", foreground=GetTextColour(), background=GetBackground() )
    style.configure("TLabelframe.Label", foreground=GetTextColour(), background=GetBackground() )
    style.configure("TCombobox", foreground=GetTextColour(), background=GetBackground() )
    style.configure("TListbox", foreground=GetTextColour(), background=GetBackground() )

    style.map("TCheckbutton", background = [('disabled', GetBackground())])
    style.map("TRadiobutton", background = [('disabled', GetBackground())])
    style.map("TButton", background = [('disabled', GetBackground())])
    style.map("TLabel", background = [('background', GetBackground())])
    style.map("TComboBox", background = [('readonly', GetBackground())])

    app = ProjectWindow(root, sdkpath, args)

    app.configure(background=GetBackground())

    root.mainloop()
    sys.exit(0)

def RunWarning(message):
    mb.showwarning('Raspberry Pi Pico Project Generator', message)
    sys.exit(0)

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
        self.grab_release()
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
        cancelButton.grid(column=5, row = 3, padx=5)
        okButton.grid(column=4, row = 3, sticky=tk.E, padx=5)

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
            else:
                self.results.pop(self.namelist.get(i), None)

        self.destroy()

    def cancel(self):
        self.destroy()

    def get(self):
        return self.results

class WirelessSettingsWindow(sd.Dialog):

    def __init__(self, parent):
        sd.Dialog.__init__(self, parent, "Wireless settings")
        self.parent = parent

    def body(self, master):
        self.configure(background=GetBackground())
        master.configure(background=GetBackground())
        self.ssid = tk.StringVar()
        self.password = tk.StringVar()

        a = ttk.Label(master, text='SSID :', background=GetBackground())
        a.grid(row=0, column=0, sticky=tk.E)
        a.configure(background=GetBackground())
        ttk.Entry(master, textvariable=self.ssid).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5)

        ttk.Label(master, text='Password :').grid(row=1, column=0, sticky=tk.E)
        ttk.Entry(master, textvariable=self.password).grid(row=1, column=1, sticky=tk.W+tk.E, padx=5)

        self.transient(self.parent)
        self.grab_set()

    def ok(self):
        self.grab_release()
        self.destroy()

    def cancel(self):
        self.destroy()

    def get(self):
        return (self.ssid.get(), self.password.get())

# Our main window
class ProjectWindow(tk.Frame):

    def __init__(self, parent, sdkpath, args):
        tk.Frame.__init__(self, parent)
        self.master = parent
        self.sdkpath = sdkpath
        self.init_window(args)
        self.configs = dict()
        self.ssid = str()
        self.password = str()

    def setState(self, thing, state):
        for child in thing.winfo_children():
            child.configure(state=state)

    def boardtype_change_callback(self, event):
        boardtype = self.boardtype.get()
        if boardtype == "pico_w":
            self.setState(self.picowSubframe, "enabled")
        else:
            self.setState(self.picowSubframe, "disabled")

    def wirelessSettings(self):
        result = WirelessSettingsWindow(self)
        self.ssid, self.password = result.get()

    def init_window(self, args):
        self.master.title("Raspberry Pi Pico Project Generator")
        self.master.configure(bg=GetBackground())

        optionsRow = 0

        mainFrame = tk.Frame(self, bg=GetBackground()).grid(row=optionsRow, column=0, columnspan=6, rowspan=12)

        # Need to keep a reference to the image or it will not appear.
        self.logo = tk.PhotoImage(file=GetFilePath("logo_alpha.gif"))
        logowidget = ttk.Label(mainFrame, image=self.logo, borderwidth=0, relief="solid").grid(row=0,column=0, columnspan=5, pady=10)

        optionsRow += 2

        namelbl = ttk.Label(mainFrame, text='Project Name :').grid(row=optionsRow, column=0, sticky=tk.E)
        self.projectName = tk.StringVar()

        if args.name != None:
            self.projectName.set(args.name)
        else:
            self.projectName.set('ProjectName')

        nameEntry = ttk.Entry(mainFrame, textvariable=self.projectName).grid(row=optionsRow, column=1, sticky=tk.W+tk.E, padx=5)

        optionsRow += 1

        locationlbl = ttk.Label(mainFrame, text='Location :').grid(row=optionsRow, column=0, sticky=tk.E)
        self.locationName = tk.StringVar()
        self.locationName.set(os.getcwd())
        locationEntry = ttk.Entry(mainFrame, textvariable=self.locationName).grid(row=optionsRow, column=1, columnspan=3, sticky=tk.W+tk.E, padx=5)
        locationBrowse = ttk.Button(mainFrame, text='Browse', command=self.browse).grid(row=3, column=4)

        optionsRow += 1

        ttk.Label(mainFrame, text = "Board Type :").grid(row=optionsRow, column=0, padx=4, sticky=tk.E)
        self.boardtype = ttk.Combobox(mainFrame, values=boardtype_list, )
        self.boardtype.grid(row=4, column=1, padx=4, sticky=tk.W+tk.E)
        self.boardtype.set('pico')
        self.boardtype.bind('<<ComboboxSelected>>',self.boardtype_change_callback)
        optionsRow += 1

        # Features section
        featuresframe = ttk.LabelFrame(mainFrame, text="Library Options", relief=tk.RIDGE, borderwidth=2)
        featuresframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=5, ipadx=5, padx=5, pady=5, sticky=tk.E+tk.W)

        s = (len(features_list)/3)

        self.feature_checkbox_vars = []
        row = 0
        col = 0
        for i in features_list:
            var = tk.StringVar(value='') # Off by default for the moment
            c = features_list[i][GUI_TEXT]
            cb = ttk.Checkbutton(featuresframe, text = c, var=var, onvalue=i, offvalue='')
            cb.grid(row=row, column=col, padx=15, pady=2, ipadx=1, ipady=1, sticky=tk.E+tk.W)
            self.feature_checkbox_vars.append(var)
            row+=1
            if row >= s:
                col+=1
                row = 0

        optionsRow += 5

        # PicoW options section
        self.picowSubframe = ttk.LabelFrame(mainFrame, relief=tk.RIDGE, borderwidth=2, text="Pico Wireless Options")
        self.picowSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=2, padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)
        self.pico_wireless = tk.StringVar()

        col = 0
        row = 0
        for i in picow_options_list:
            rb = ttk.Radiobutton(self.picowSubframe, text=picow_options_list[i][GUI_TEXT], variable=self.pico_wireless, val=i)
            rb.grid(row=row, column=col,  padx=15, pady=1, sticky=tk.E+tk.W)
            col+=1
            if col == 3:
                col=0
                row+=1

        # DOnt actually need any settings at the moment.
        # ttk.Button(self.picowSubframe, text='Settings', command=self.wirelessSettings).grid(row=0, column=4, padx=5, pady=2, sticky=tk.E)

        self.setState(self.picowSubframe, "disabled")

        optionsRow += 3

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
        coptionsSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=3, padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)

        self.wantExamples = tk.IntVar()
        self.wantExamples.set(args.examples)
        ttk.Checkbutton(coptionsSubframe, text="Add examples for Pico library", variable=self.wantExamples).grid(row=0, column=0, padx=4, sticky=tk.W)

        self.wantRunFromRAM = tk.IntVar()
        self.wantRunFromRAM.set(args.runFromRAM)
        ttk.Checkbutton(coptionsSubframe, text="Run from RAM", variable=self.wantRunFromRAM).grid(row=0, column=1, padx=4, sticky=tk.W)

        self.wantCPP = tk.IntVar()
        self.wantCPP.set(args.cpp)
        ttk.Checkbutton(coptionsSubframe, text="Generate C++", variable=self.wantCPP).grid(row=0, column=3, padx=4, sticky=tk.W)

        ttk.Button(coptionsSubframe, text="Advanced...", command=self.config).grid(row=0, column=4, sticky=tk.E)

        self.wantCPPExceptions = tk.IntVar()
        self.wantCPPExceptions.set(args.cppexceptions)
        ttk.Checkbutton(coptionsSubframe, text="Enable C++ exceptions", variable=self.wantCPPExceptions).grid(row=1, column=0, padx=4, sticky=tk.W)

        self.wantCPPRTTI = tk.IntVar()
        self.wantCPPRTTI.set(args.cpprtti)
        ttk.Checkbutton(coptionsSubframe, text="Enable C++ RTTI", variable=self.wantCPPRTTI).grid(row=1, column=1, padx=4, sticky=tk.W)

        optionsRow += 3

        # Build Options section

        boptionsSubframe = ttk.LabelFrame(mainFrame, relief=tk.RIDGE, borderwidth=2, text="Build Options")
        boptionsSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=2, padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)

        self.wantBuild = tk.IntVar()
        self.wantBuild.set(args.build)
        ttk.Checkbutton(boptionsSubframe, text="Run build after generation", variable=self.wantBuild).grid(row=0, column=0, padx=4, sticky=tk.W)

        self.wantOverwrite = tk.IntVar()
        self.wantOverwrite.set(args.overwrite)
        ttk.Checkbutton(boptionsSubframe, text="Overwrite existing projects", variable=self.wantOverwrite).grid(row=0, column=1, padx=4, sticky=tk.W)

        optionsRow += 2
        
        # IDE Options section

        vscodeoptionsSubframe = ttk.LabelFrame(mainFrame, relief=tk.RIDGE, borderwidth=2, text="IDE Options")
        vscodeoptionsSubframe.grid_columnconfigure(2, weight=1)
        vscodeoptionsSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=2, padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)

        self.wantVSCode = tk.IntVar()
        if args.project is None:
            self.wantVSCode.set(False)
        else:
            self.wantVSCode.set('vscode' in args.project)
        ttk.Checkbutton(vscodeoptionsSubframe, text="Create VSCode project", variable=self.wantVSCode).grid(row=0, column=0, padx=4, sticky=tk.W)

        ttk.Label(vscodeoptionsSubframe, text = "     Debugger:").grid(row=0, column=1, padx=4, sticky=tk.W)

        self.debugger = ttk.Combobox(vscodeoptionsSubframe, values=debugger_list, state="readonly")
        self.debugger.grid(row=0, column=2, padx=4, sticky=tk.EW)
        self.debugger.current(args.debugger)

        optionsRow += 2

        # OK, Cancel, Help section
        # creating buttons
        QuitButton = ttk.Button(mainFrame, text="Quit", command=self.quit).grid(row=optionsRow, column=4, stick=tk.E, padx=10, pady=5)
        OKButton = ttk.Button(mainFrame, text="OK", command=self.OK).grid(row=optionsRow, column=3, padx=4, pady=5, sticky=tk.E)

        # TODO help not implemented yet
        # HelpButton = ttk.Button(mainFrame, text="Help", command=self.help).grid(row=optionsRow, column=0, pady=5)

        # You can set a default path here, replace the string with whereever you want.
        # self.locationName.set('/home/pi/pico_projects')

    def GetFeatures(self):
        features = []

        i = 0
        for cb in self.feature_checkbox_vars:
            s = cb.get()
            if s != '':
                features.append(s)

        picow_extra = self.pico_wireless.get()

        if picow_extra != 'picow_none':
            features.append(picow_extra)

        return features

    def quit(self):
        # TODO Check if we want to exit here
        sys.exit(0)

    def OK(self):
        # OK, grab all the settings from the page, then call the generators
        projectPath = self.locationName.get()
        features = self.GetFeatures()
        projects = list()
        if (self.wantVSCode.get()):
            projects.append("vscode")

        params={
                'sdkPath'       : self.sdkpath,
                'projectRoot'   : Path(projectPath),
                'projectName'   : self.projectName.get(),
                'wantGUI'       : True,
                'wantOverwrite' : self.wantOverwrite.get(),
                'wantBuild'     : self.wantBuild.get(),
                'boardtype'     : self.boardtype.get(),
                'features'      : features,
                'projects'      : projects,
                'configs'       : self.configs,
                'wantRunFromRAM': self.wantRunFromRAM.get(),
                'wantExamples'  : self.wantExamples.get(),
                'wantUART'      : self.wantUART.get(),
                'wantUSB'       : self.wantUSB.get(),
                'wantCPP'       : self.wantCPP.get(),
                'debugger'      : self.debugger.current(),
                'exceptions'    : self.wantCPPExceptions.get(),
                'rtti'          : self.wantCPPRTTI.get(),
                'ssid'          : self.ssid,
                'password'      : self.password,
                }

        DoEverything(self, params)

    def browse(self):
        name = fd.askdirectory()
        self.locationName.set(name)

    def help(self):
        print("Help TODO")

    def config(self):
        # Run the configuration window
        self.configs = ConfigurationWindow(self, self.configs).get()

def CheckPrerequisites():
    global isMac, isWindows
    isMac = (platform.system() == 'Darwin')
    isWindows = (platform.system() == 'Windows')

    # Do we have a compiler?
    return shutil.which(COMPILER_NAME)


def CheckSDKPath(gui):
    sdkPath = os.getenv('PICO_SDK_PATH')

    if sdkPath == None:
        m = 'Unable to locate the Raspberry Pi Pico SDK, PICO_SDK_PATH is not set'
        if (gui):
            RunWarning(m)
        else:
            print(m)
    elif not os.path.isdir(sdkPath):
        m = 'Unable to locate the Raspberry Pi Pico SDK, PICO_SDK_PATH does not point to a directory'
        if (gui):
            RunWarning(m)
        else:
            print(m)
        sdkPath = None

    return sdkPath

def GetFilePath(filename):
    if os.path.islink(__file__):
        script_file = os.readlink(__file__)
    else:
        script_file = __file__
    return os.path.join(os.path.dirname(script_file), filename)

def ParseCommandLine():
    debugger_flags = ', '.join('{} = {}'.format(i, v) for i, v in enumerate(debugger_list))
    parser = argparse.ArgumentParser(description='Pico Project generator')
    parser.add_argument("name", nargs="?", help="Name of the project")
    parser.add_argument("-t", "--tsv", help="Select an alternative pico_configs.tsv file", default=GetFilePath("pico_configs.tsv"))
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
    parser.add_argument("-usb", "--usb", action='store_true', help="Console output to USB (disables other USB functionality")
    parser.add_argument("-cpp", "--cpp", action='store_true', default=0, help="Generate C++ code")
    parser.add_argument("-cpprtti", "--cpprtti", action='store_true', default=0, help="Enable C++ RTTI (Uses more memory)")
    parser.add_argument("-cppex", "--cppexceptions", action='store_true', default=0, help="Enable C++ exceptions (Uses more memory)")
    parser.add_argument("-d", "--debugger", type=int, help="Select debugger ({})".format(debugger_flags), default=0)
    parser.add_argument("-board", "--boardtype", action="store", default='pico', help="Select board type (see --boardlist for available boards)")
    parser.add_argument("-bl", "--boardlist", action="store_true", help="List available board types")
    parser.add_argument("-cp", "--cpath", help="Override default VSCode compiler path")

    return parser.parse_args()


def GenerateMain(folder, projectName, features, cpp):

    if cpp:
        filename = Path(folder) / (projectName + '.cpp')
    else:
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
                o = f'#include "{features_list[feat][H_FILE]}"\n'
                file.write(o)
            if (feat in stdlib_examples_list):
                o = f'#include "{stdlib_examples_list[feat][H_FILE]}"\n'
                file.write(o)
            if (feat in picow_options_list):
                o = f'#include "{picow_options_list[feat][H_FILE]}"\n'
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
   
    filename = Path(folder) / CMAKELIST_FILENAME
    projectName = params['projectName']
    board_type = params['boardtype']

    # OK, for the path, CMake will accept forward slashes on Windows, and thats
    # seemingly a bit easier to handle than the backslashes
    p = str(params['sdkPath']).replace('\\','/')
    sdk_path = f'"{p}"'

    cmake_header1 = (f"# Generated Cmake Pico project file\n\n"
                 "cmake_minimum_required(VERSION 3.13)\n\n"
                 "set(CMAKE_C_STANDARD 11)\n"
                 "set(CMAKE_CXX_STANDARD 17)\n\n"
                 "# Initialise pico_sdk from installed location\n"
                 "# (note this can come from environment, CMake cache etc)\n"
                 f"set(PICO_SDK_PATH {sdk_path})\n\n"
                 f"set(PICO_BOARD {board_type} CACHE STRING \"Board type\")\n\n"
                 "# Pull in Raspberry Pi Pico SDK (must be before project)\n"
                 "include(pico_sdk_import.cmake)\n\n"
                 "if (PICO_SDK_VERSION_STRING VERSION_LESS \"1.4.0\")\n"
                 "  message(FATAL_ERROR \"Raspberry Pi Pico SDK version 1.4.0 (or later) required. Your version is ${PICO_SDK_VERSION_STRING}\")\n"
                 "endif()\n\n"
                 f"project({projectName} C CXX ASM)\n"
                )
    
    cmake_header3 = (
                "\n# Initialise the Raspberry Pi Pico SDK\n"
                "pico_sdk_init()\n\n"
                "# Add executable. Default name is the project name, version 0.1\n\n"
                )


    file = open(filename, 'w')

    file.write(cmake_header1)

    if params['exceptions']:
        file.write("\nset(PICO_CXX_ENABLE_EXCEPTIONS 1)\n")

    if params['rtti']:
        file.write("\nset(PICO_CXX_ENABLE_RTTI 1)\n")

    file.write(cmake_header3)

    # add the preprocessor defines for overall configuration
    if params['configs']:
        file.write('# Add any PICO_CONFIG entries specified in the Advanced settings\n')
        for c, v in params['configs'].items():
            if v == "True":
                v = "1"
            elif v == "False":
                v = "0"
            file.write(f'add_compile_definitions({c} = {v})\n')
        file.write('\n')

    # No GUI/command line to set a different executable name at this stage
    executableName = projectName

    if params['wantCPP']:
        file.write(f'add_executable({projectName} {projectName}.cpp )\n\n')
    else:
        file.write(f'add_executable({projectName} {projectName}.c )\n\n')

    file.write(f'pico_set_program_name({projectName} "{executableName}")\n')
    file.write(f'pico_set_program_version({projectName} "0.1")\n\n')

    if params['wantRunFromRAM']:
        file.write(f'# no_flash means the target is to run from RAM\n')
        file.write(f'pico_set_binary_type({projectName} no_flash)\n\n')

    # Console output destinations
    if params['wantUART']:
        file.write(f'pico_enable_stdio_uart({projectName} 1)\n')
    else:
        file.write(f'pico_enable_stdio_uart({projectName} 0)\n')

    if params['wantUSB']:
        file.write(f'pico_enable_stdio_usb({projectName} 1)\n\n')
    else:
        file.write(f'pico_enable_stdio_usb({projectName} 0)\n\n')

    # If we need wireless, check for SSID and password
    # removed for the moment as these settings are currently only needed for the pico-examples
    # but may be required in here at a later date.
    if False:
        if 'ssid' in params or 'password' in params:
            file.write('# Add any wireless access point information\n')
            file.write(f'target_compile_definitions({projectName} PRIVATE\n')
            if 'ssid' in params:
                file.write(f'WIFI_SSID=\" {params["ssid"]} \"\n')
            else:
                file.write(f'WIFI_SSID=\"${WIFI_SSID}\"')

            if 'password' in params:
                file.write(f'WIFI_PASSWORD=\"{params["password"]}\"\n')
            else:
                file.write(f'WIFI_PASSWORD=\"${WIFI_PASSWORD}\"')
            file.write(')\n\n')

    # Standard libraries
    file.write('# Add the standard library to the build\n')
    file.write(f'target_link_libraries({projectName}\n')
    file.write("        " + STANDARD_LIBRARIES)
    file.write(')\n\n')

    # Standard include directories
    file.write('# Add the standard include files to the build\n')
    file.write(f'target_include_directories({projectName} PRIVATE\n')
    file.write("  ${CMAKE_CURRENT_LIST_DIR}\n")
    file.write("  ${CMAKE_CURRENT_LIST_DIR}/.. # for our common lwipopts or any other standard includes, if required\n")
    file.write(')\n\n')

    # Selected libraries/features
    if (params['features']):
        file.write('# Add any user requested libraries\n')
        file.write(f'target_link_libraries({projectName} \n')
        for feat in params['features']:
            if (feat in features_list):
                file.write("        " + features_list[feat][LIB_NAME] + '\n')
            if (feat in picow_options_list):
                file.write("        " + picow_options_list[feat][LIB_NAME] + '\n')
        file.write('        )\n\n')

    file.write(f'pico_add_extra_outputs({projectName})\n\n')

    file.close()


# Generates the requested project files, if any
def generateProjectFiles(projectPath, projectName, sdkPath, projects, debugger):

    oldCWD = os.getcwd()

    os.chdir(projectPath)

    debugger = debugger_config_list[debugger]
    gdbPath =  "arm-none-eabi-gdb" if isWindows else "gdb-multiarch"
    # Need to escape windows files paths backslashes
    cPath = str(compilerPath).replace('\\', '\\\\' )

    for p in projects :
        if p == 'vscode':
            launch = ('{\n'
                  '  "version": "0.2.0",\n'
                  '  "configurations": [\n'
                  '    {\n'
                  '      "name": "Pico Debug (Cortex-Debug)",\n'
                  '      "cwd": "${workspaceRoot}",\n'
                  '      "executable": "${command:cmake.launchTargetPath}",\n'
                  '      "request": "launch",\n'
                  '      "type": "cortex-debug",\n'
                  '      "servertype": "openocd",\n'
                  f'      "gdbPath": "{gdbPath}",\n'
                  '      "device": "RP2040",\n'
                  '      "configFiles": [\n'
                  f'        "interface/{debugger}",\n'
                  '        "target/rp2040.cfg"\n'
                  '        ],\n'
                  '      "svdFile": "${env:PICO_SDK_PATH}/src/rp2040/hardware_regs/rp2040.svd",\n'
                  '      "runToEntryPoint": "main",\n'
                  '      // Give restart the same functionality as runToEntryPoint - main\n'
                  '      "postRestartCommands": [\n'
                  '          "break main",\n'
                  '          "continue"\n'
                  '      ],\n'
                  '      "openOCDLaunchCommands": [\n'
                  '          "adapter speed 5000"\n'
                  '      ]\n'
                  '    },\n'
                  '    {\n'
                  '      "name": "Pico Debug (Cortex-Debug with external OpenOCD)",\n'
                  '      "cwd": "${workspaceRoot}",\n'
                  '      "executable": "${command:cmake.launchTargetPath}",\n'
                  '      "request": "launch",\n'
                  '      "type": "cortex-debug",\n'
                  '      "servertype": "external",\n'
                  '      "gdbTarget": "localhost:3333",\n'
                  f'      "gdbPath": "{gdbPath}",\n'
                  '      "device": "RP2040",\n'
                  '      "svdFile": "${env:PICO_SDK_PATH}/src/rp2040/hardware_regs/rp2040.svd",\n'
                  '      "runToEntryPoint": "main",\n'
                  '      // Give restart the same functionality as runToEntryPoint - main\n'
                  '      "postRestartCommands": [\n'
                  '          "break main",\n'
                  '          "continue"\n'
                  '      ]\n'
                  '    },\n'
                  '    {\n'
                  '      "name": "Pico Debug (C++ Debugger)",\n'
                  '      "type": "cppdbg",\n'
                  '      "request": "launch",\n'
                  '      "cwd": "${workspaceRoot}",\n'
                  '      "program": "${command:cmake.launchTargetPath}",\n'
                  '      "MIMode": "gdb",\n'
                  '      "miDebuggerPath": "{gdbPath}",\n'
                  '      "miDebuggerServerAddress": "localhost:3333",\n'
                  '      "debugServerPath": "openocd",\n'
                  '      "debugServerArgs": "-f interface/cmsis-dap.cfg -f target/rp2040.cfg -c \\"adapter speed 5000\\"",\n'
                  '      "serverStarted": "Listening on port .* for gdb connections",\n'
                  '      "filterStderr": true,\n'
                  '      "stopAtEntry": true,\n'
                  '      "hardwareBreakpoints": {\n'
                  '        "require": true,\n'
                  '        "limit": 4\n'
                  '      },\n'
                  '      "preLaunchTask": "Flash",\n'
                  '      "svdPath": "${env:PICO_SDK_PATH}/src/rp2040/hardware_regs/rp2040.svd"\n'
                  '    },\n'
                  '  ]\n'
                  '}\n')

            properties = ('{\n'
                  '  "configurations": [\n'
                  '    {\n'
                  '      "name": "Pico",\n'
                  '      "includePath": [\n'
                  '        "${workspaceFolder}/**",\n'
                  '        "${env:PICO_SDK_PATH}/**"\n'
                  '      ],\n'
                  '      "defines": [],\n'
                  f'      "compilerPath": "{cPath}",\n'
                  '      "cStandard": "c17",\n'
                  '      "cppStandard": "c++14",\n'
                  '      "intelliSenseMode": "linux-gcc-arm",\n'
                  '      "configurationProvider" : "ms-vscode.cmake-tools"\n'
                  '    }\n'
                  '  ],\n'
                  '  "version": 4\n'
                  '}\n')

            settings = ( '{\n'
                   '  "cmake.statusbar.advanced": {\n'
                   '    "debug": {\n'
                   '      "visibility": "hidden"\n'
                   '    },\n'
                   '    "launch": {\n'
                   '      "visibility": "hidden"\n'
                   '    },\n'
                   '    "build": {\n'
                   '      "visibility": "hidden"\n'
                   '    },\n'
                   '    "buildTarget": {\n'
                   '      "visibility": "hidden"\n'
                   '    }\n'
                   '  },\n'
                   '  "cmake.buildBeforeRun": true,\n'
                   '  "cmake.configureOnOpen": true,\n'
                   '  "cmake.configureSettings": {\n'
                   '    "CMAKE_MODULE_PATH": "${env:PICO_INSTALL_PATH}/pico-sdk-tools"\n'
                   '  },\n'
                   '  "cmake.generator": "Ninja",\n'
                   '  "C_Cpp.default.configurationProvider": "ms-vscode.cmake-tools"\n'
                   '}\n')

            extensions = ( '{\n'
                   '  "recommendations": [\n'
                   '    "marus25.cortex-debug",\n'
                   '    "ms-vscode.cmake-tools",\n'
                   '    "ms-vscode.cpptools",\n'
                   '    "ms-vscode.cpptools-extension-pack",\n'
                   '    "ms-vscode.vscode-serial-monitor"\n'
                   '  ]\n'
                   '}\n')

            # Create a build folder, and run our cmake project build from it
            if not os.path.exists(VSCODE_FOLDER):
                os.mkdir(VSCODE_FOLDER)

            os.chdir(VSCODE_FOLDER)

            filename = VSCODE_LAUNCH_FILENAME
            file = open(filename, 'w')
            file.write(launch)
            file.close()

            file = open(VSCODE_C_PROPERTIES_FILENAME, 'w')
            file.write(properties)
            file.close()

            file = open(VSCODE_SETTINGS_FILENAME, 'w')
            file.write(settings)
            file.close()

            file = open(VSCODE_EXTENSIONS_FILENAME, 'w')
            file.write(extensions)
            file.close()

        else :
            print('Unknown project type requested')

    os.chdir(oldCWD)


def LoadConfigurations():
    try:
        with open(args.tsv) as tsvfile:
            reader = csv.DictReader(tsvfile, dialect='excel-tab')
            for row in reader:
                configuration_dictionary.append(row)
    except:
        print("No Pico configurations file found. Continuing without")

def LoadBoardTypes(sdkPath):
    # Scan the boards folder for all header files, extract filenames, and make a list of the results
    # default folder is <PICO_SDK_PATH>/src/boards/include/boards/*
    # If the PICO_BOARD_HEADER_DIRS environment variable is set, use that as well

    loc = sdkPath / "src/boards/include/boards"
    boards=[]
    for x in Path(loc).iterdir():
        if x.suffix == '.h':
            boards.append(x.stem)

    loc = os.getenv('PICO_BOARD_HEADER_DIRS')

    if loc != None:
        for x in Path(loc).iterdir():
            if x.suffix == '.h':
                boards.append(x.stem)

    return boards

def DoEverything(parent, params):

    if not os.path.exists(params['projectRoot']):
        if params['wantGUI']:
            mb.showerror('Raspberry Pi Pico Project Generator', 'Invalid project path. Select a valid path and try again')
            return
        else:
            print('Invalid project path')
            sys.exit(-1)

    oldCWD = os.getcwd()
    os.chdir(params['projectRoot'])

    # Create our project folder as subfolder
    os.makedirs(params['projectName'], exist_ok=True)

    os.chdir(params['projectName'])

    projectPath = params['projectRoot'] / params['projectName']

    # First check if there is already a project in the folder
    # If there is we abort unless the overwrite flag it set
    if os.path.exists(CMAKELIST_FILENAME):
        if not params['wantOverwrite'] :
            if params['wantGUI']:
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
    shutil.copyfile(params['sdkPath'] / 'external' / 'pico_sdk_import.cmake', projectPath / 'pico_sdk_import.cmake' )

    if params['features']:
        features_and_examples = params['features'][:]
    else:
        features_and_examples= []

    if params['wantExamples']:
        features_and_examples = list(stdlib_examples_list.keys()) + features_and_examples

    GenerateMain('.', params['projectName'], features_and_examples, params['wantCPP'])

    GenerateCMake('.', params)

    # If we have any ancilliary files, copy them to our project folder
    # Currently only the picow with lwIP support needs an extra file, so just check that list
    for feat in features_and_examples:
        if feat in picow_options_list:
            if picow_options_list[feat][ANCILLARY_FILE] != "":
                shutil.copy(sourcefolder + "/" + picow_options_list[feat][ANCILLARY_FILE], projectPath / picow_options_list[feat][ANCILLARY_FILE])

    # Create a build folder, and run our cmake project build from it
    if not os.path.exists('build'):
        os.mkdir('build')

    os.chdir('build')

    # If we are overwriting a previous project, we should probably clear the folder, but that might delete something the users thinks is important, so
    # for the moment, just delete the CMakeCache.txt file as certain changes may need that to be recreated.

    if os.path.exists(CMAKECACHE_FILENAME):
        os.remove(CMAKECACHE_FILENAME)

    cpus = os.cpu_count()
    if cpus == None:
        cpus = 1

    if isWindows:
        # Had a special case report, when using MinGW, need to check if using nmake or mingw32-make.
        if shutil.which("mingw32-make"):
            # Assume MinGW environment
            cmakeCmd = 'cmake -DCMAKE_BUILD_TYPE=Debug -G "MinGW Makefiles" ..'
            makeCmd = 'mingw32-make '
        elif shutil.which("ninja"):
            # When installing SDK version 1.5.0 on windows with installer pico-setup-windows-x64-standalone.exe, ninja is used 
            cmakeCmd = 'cmake -DCMAKE_BUILD_TYPE=Debug -G Ninja ..'
            makeCmd = 'ninja '        
        else:
            # Everything else assume nmake
            cmakeCmd = 'cmake -DCMAKE_BUILD_TYPE=Debug -G "NMake Makefiles" ..'
            makeCmd = 'nmake '
    else:
        # Ninja now works OK under Linux, so if installed use it by default. It's faster.
        if shutil.which("ninja"):
            cmakeCmd = 'cmake -DCMAKE_BUILD_TYPE=Debug -G Ninja ..'
            makeCmd = 'ninja '
        else:
            cmakeCmd = 'cmake -DCMAKE_BUILD_TYPE=Debug ..'
            makeCmd = 'make -j' + str(cpus)

    if params['wantGUI']:
        RunCommandInWindow(parent, cmakeCmd)
    else:
        os.system(cmakeCmd)

    if params['projects']:
        generateProjectFiles(projectPath, params['projectName'], params['sdkPath'], params['projects'], params['debugger'])

    if params['wantBuild']:
        if params['wantGUI']:
            RunCommandInWindow(parent, makeCmd)
        else:
            os.system(makeCmd)
            print('\nIf the application has built correctly, you can now transfer it to the Raspberry Pi Pico board')

    os.chdir(oldCWD)


###################################################################################
# main execution starteth here

sourcefolder = os.path.dirname(os.path.abspath(__file__))

args = ParseCommandLine()

if args.nouart:
    args.uart = False

if args.debugger > len(debugger_list) - 1:
    args.debugger = 0

# Check we have everything we need to compile etc
c = CheckPrerequisites()

## TODO Do both warnings in the same error message so user does have to keep coming back to find still more to do

if c == None:
    m = f'Unable to find the `{COMPILER_NAME}` compiler\n'
    m +='You will need to install an appropriate compiler to build a Raspberry Pi Pico project\n'
    m += 'See the Raspberry Pi Pico documentation for how to do this on your particular platform\n'

    if (args.gui):
        RunWarning(m)
    else:
        print(m)
    sys.exit(-1)

if args.name == None and not args.gui and not args.list and not args.configs and not args.boardlist:
    print("No project name specfied\n")
    sys.exit(-1)

# Check if we were provided a compiler path, and override the default if so
if args.cpath:
    compilerPath = Path(args.cpath)
else:
    compilerPath = Path(c)

# load/parse any configuration dictionary we may have
LoadConfigurations()

p = CheckSDKPath(args.gui)

if p == None:
    sys.exit(-1)

sdkPath = Path(p)

boardtype_list = LoadBoardTypes(sdkPath)
boardtype_list.sort()

if args.gui:
    RunGUI(sdkPath, args) # does not return, only exits

projectRoot = Path(os.getcwd())

if args.list or args.configs or args.boardlist:
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

    if args.boardlist:
        print("Available board types:\n")
        for board in boardtype_list:
            print(board)
        print('\n')

    sys.exit(0)
else :
    params={
        'sdkPath'       : sdkPath,
        'projectRoot'   : projectRoot,
        'projectName'   : args.name,
        'wantGUI'       : False,
        'wantOverwrite' : args.overwrite,
        'boardtype'     : args.boardtype,
        'wantBuild'     : args.build,
        'features'      : args.feature,
        'projects'      : args.project,
        'configs'       : (),
        'wantRunFromRAM': args.runFromRAM,
        'wantExamples'  : args.examples,
        'wantUART'      : args.uart,
        'wantUSB'       : args.usb,
        'wantCPP'       : args.cpp,
        'debugger'      : args.debugger,
        'exceptions'    : args.cppexceptions,
        'rtti'          : args.cpprtti,
        'ssid'          : '',
        'password'      : '',
        }

    DoEverything(None, params)
