#
# Copyright (c) 2021 Raspberry Pi (Trading) Ltd.
#
# SPDX-License-Identifier: BSD-3-Clause
#

"""
gui -- setup for the pico-project-generator graphical user interface
"""

import tkinter as tk
from tkinter import messagebox as mb
from tkinter import filedialog as fd
from tkinter import simpledialog as sd
from tkinter import ttk


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

    ttk.Style().configure("TButton", padding=6, relief="groove", border=2,
                          foreground=GetButtonTextColour(), background=GetButtonBackground())
    ttk.Style().configure("TLabel", foreground=GetTextColour(), background=GetBackground())
    ttk.Style().configure("TCheckbutton", foreground=GetTextColour(), background=GetBackground())
    ttk.Style().configure("TRadiobutton", foreground=GetTextColour(), background=GetBackground())
    ttk.Style().configure("TLabelframe", foreground=GetTextColour(), background=GetBackground())
    ttk.Style().configure("TLabelframe.Label", foreground=GetTextColour(), background=GetBackground())
    ttk.Style().configure("TCombobox", foreground=GetTextColour(), background=GetBackground())
    ttk.Style().configure("TListbox", foreground=GetTextColour(), background=GetBackground())

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
            var = tk.StringVar(value='')  # Off by default for the moment
            self.vars.append(var)
            cb = ttk.Checkbutton(self, var=var, text=c,
                                 onvalue=c, offvalue="",
                                 width=20)
            cb.pack(side="top", fill="x", anchor="w")

    def getCheckedItems(self):
        values = []
        for var in self.vars:
            value = var.get()
            if value:
                values.append(value)
        return values


def thread_function(text, command, ok):
    l = shlex.split(command)
    proc = subprocess.Popen(l, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(proc.stdout.readline, ''):
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
        self.input = tk.Entry(self)
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
        # self.configure(background=GetBackground())
        values = self.config_item['enumvalues'].split('|')
        values.insert(0, 'Not set')
        self.input = ttk.Combobox(self, values=values, state='readonly')
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
        ttk.Label(self, text="Select the advanced options you wish to enable or change. Note that you really should understand the implications of changing these items before using them!").grid(
            row=0, column=0, columnspan=5)
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

        # Make a list of our list boxes to make it all easier to handle
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
            i += 1

        self.descriptionText.grid(row=3, column=0, columnspan=4, sticky=tk.W + tk.E)
        cancelButton.grid(column=4, row=3, sticky=tk.E, padx=5)
        okButton.grid(column=5, row=3, padx=5)

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
                self.valuelist.itemconfig(self.valuelist.size() - 1, {'bg': 'green'})

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
                    self.descriptionText.delete(1.0, tk.END)
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
                elif (conf['type'] == 'int' or conf['type'] == ""):  # "" defaults to int
                    result = EditIntWindow(self, conf, self.valuelist.get(index)).get()
                elif conf['type'] == 'enum':
                    result = EditEnumWindow(self, conf, self.valuelist.get(index)).get()

                # Update the valuelist with our new item
                self.valuelist.delete(index)
                self.valuelist.insert(index, result)
                if result != CONFIG_UNSET:
                    self.valuelist.itemconfig(index, {'bg': 'green'})
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
        logowidget = ttk.Label(
            mainFrame, image=self.logo, borderwidth=0, relief="solid").grid(
            row=0, column=0, columnspan=5, pady=10)

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
        locationEntry = ttk.Entry(
            mainFrame, textvariable=self.locationName).grid(
            row=3, column=1, columnspan=3, sticky=tk.W + tk.E, padx=5)
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
        ooptionsSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=2,
                              padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)

        self.wantUART = tk.IntVar()
        self.wantUART.set(args.uart)
        ttk.Checkbutton(
            ooptionsSubframe, text="Console over UART", variable=self.wantUART).grid(
            row=0, column=0, padx=4, sticky=tk.W)

        self.wantUSB = tk.IntVar()
        self.wantUSB.set(args.usb)
        ttk.Checkbutton(ooptionsSubframe, text="Console over USB (Disables other USB use)",
                        variable=self.wantUSB).grid(row=0, column=1, padx=4, sticky=tk.W)

        optionsRow += 2

        # Code options section
        coptionsSubframe = ttk.LabelFrame(mainFrame, relief=tk.RIDGE, borderwidth=2, text="Code Options")
        coptionsSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=3,
                              padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)

        self.wantExamples = tk.IntVar()
        self.wantExamples.set(args.examples)
        ttk.Checkbutton(coptionsSubframe, text="Add examples for Pico library",
                        variable=self.wantExamples).grid(row=0, column=0, padx=4, sticky=tk.W)

        self.wantRunFromRAM = tk.IntVar()
        self.wantRunFromRAM.set(args.runFromRAM)
        ttk.Checkbutton(
            coptionsSubframe, text="Run from RAM", variable=self.wantRunFromRAM).grid(
            row=0, column=1, padx=4, sticky=tk.W)

        self.wantCPP = tk.IntVar()
        self.wantCPP.set(args.cpp)
        ttk.Checkbutton(coptionsSubframe, text="Generate C++",
                        variable=self.wantCPP).grid(row=0, column=3, padx=4, sticky=tk.W)

        ttk.Button(coptionsSubframe, text="Advanced...", command=self.config).grid(row=0, column=4, sticky=tk.E)

        self.wantCPPExceptions = tk.IntVar()
        self.wantCPPExceptions.set(args.cppexceptions)
        ttk.Checkbutton(coptionsSubframe, text="Enable C++ exceptions",
                        variable=self.wantCPPExceptions).grid(row=1, column=0, padx=4, sticky=tk.W)

        self.wantCPPRTTI = tk.IntVar()
        self.wantCPPRTTI.set(args.cpprtti)
        ttk.Checkbutton(coptionsSubframe, text="Enable C++ RTTI",
                        variable=self.wantCPPRTTI).grid(row=1, column=1, padx=4, sticky=tk.W)

        optionsRow += 3

        # Build Options section

        boptionsSubframe = ttk.LabelFrame(mainFrame, relief=tk.RIDGE, borderwidth=2, text="Build Options")
        boptionsSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=2,
                              padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)

        self.wantBuild = tk.IntVar()
        self.wantBuild.set(args.build)
        ttk.Checkbutton(boptionsSubframe, text="Run build after generation",
                        variable=self.wantBuild).grid(row=0, column=0, padx=4, sticky=tk.W)

        self.wantOverwrite = tk.IntVar()
        self.wantOverwrite.set(args.overwrite)
        ttk.Checkbutton(boptionsSubframe, text="Overwrite project if it already exists",
                        variable=self.wantOverwrite).grid(row=0, column=1, padx=4, sticky=tk.W)

        optionsRow += 2

        vscodeoptionsSubframe = ttk.LabelFrame(mainFrame, relief=tk.RIDGE, borderwidth=2, text="IDE Options")
        vscodeoptionsSubframe.grid(row=optionsRow, column=0, columnspan=5, rowspan=2,
                                   padx=5, pady=5, ipadx=5, ipady=3, sticky=tk.E+tk.W)

        self.wantVSCode = tk.IntVar()
        ttk.Checkbutton(vscodeoptionsSubframe, text="Create VSCode project",
                        variable=self.wantVSCode).grid(row=0, column=0, padx=4, sticky=tk.W)

        ttk.Label(vscodeoptionsSubframe, text="     Debugger:").grid(row=0, column=1, padx=4, sticky=tk.W)

        self.debugger = ttk.Combobox(vscodeoptionsSubframe, values=debugger_list, state="readonly")
        self.debugger.grid(row=0, column=2, padx=4, sticky=tk.W)
        self.debugger.current(args.debugger)

        optionsRow += 2

        # OK, Cancel, Help section
        # creating buttons
        QuitButton = ttk.Button(
            mainFrame, text="Quit", command=self.quit).grid(
            row=optionsRow, column=3, padx=4, pady=5, sticky=tk.E)
        OKButton = ttk.Button(mainFrame, text="OK", command=self.OK).grid(
            row=optionsRow, column=4, stick=tk.E, padx=10, pady=5)
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
            if features_list[feat][GUI_TEXT] in f:
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
        if (self.wantVSCode.get()):
            projects.append("vscode")

        p = Parameters(
            sdkPath=self.sdkpath, projectRoot=Path(projectPath),
            projectName=self.projectName.get(),
            gui=True, overwrite=self.wantOverwrite.get(),
            build=self.wantBuild.get(),
            features=features, projects=projects, configs=self.configs, runFromRAM=self.wantRunFromRAM.get(),
            examples=self.wantExamples.get(),
            uart=self.wantUART.get(),
            usb=self.wantUSB.get(),
            cpp=self.wantCPP.get(),
            debugger=self.debugger.current(),
            exceptions=self.wantCPPExceptions.get(),
            rtti=self.wantCPPRTTI.get())

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
