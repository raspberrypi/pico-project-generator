# pico-project-generator

This is a command line or GUI tool, written in Python, to automatically generate a Pico C SDK Project.

The tool will generate all required CMake files, program files and VSCode IDE files for the set of features requested.

It will also add example code for any features and optionally for some standard library functions.

## Command line

Running `./pico_project.py --help` will give a list of the available command line parameters

```
usage: pico_project.py [-h] [-t TSV] [-o OUTPUT] [-x] [-l] [-c] [-f FEATURE] [-over] [-b] [-g] [-p PROJECT] [-r] [-uart] [-nouart] [-usb] [-cpp]
                       [-cpprtti] [-cppex] [-d DEBUGGER] [-board BOARDTYPE] [-bl]
                       [name]

Pico Project generator

positional arguments:
  name                  Name of the project

optional arguments:
  -h, --help            show this help message and exit
  -t TSV, --tsv TSV     Select an alternative pico_configs.tsv file
  -o OUTPUT, --output OUTPUT
                        Set an alternative CMakeList.txt filename
  -x, --examples        Add example code for the Pico standard library
  -l, --list            List available features
  -c, --configs         List available project configuration items
  -f FEATURE, --feature FEATURE
                        Add feature to generated project
  -over, --overwrite    Overwrite any existing project AND files
  -b, --build           Build after project created
  -g, --gui             Run a GUI version of the project generator
  -p PROJECT, --project PROJECT
                        Generate projects files for IDE. Options are: vscode
  -r, --runFromRAM      Run the program from RAM rather than flash
  -uart, --uart         Console output to UART (default)
  -nouart, --nouart     Disable console output to UART
  -usb, --usb           Console output to USB (disables other USB functionality
  -cpp, --cpp           Generate C++ code
  -cpprtti, --cpprtti   Enable C++ RTTI (Uses more memory)
  -cppex, --cppexceptions
                        Enable C++ exceptions (Uses more memory)
  -d DEBUGGER, --debugger DEBUGGER
                        Select debugger (0 = SWD, 1 = PicoProbe)
  -board BOARDTYPE, --boardtype BOARDTYPE
                        Select board type (see --boardlist for available boards)
  -bl, --boardlist      List available board types

```
You can list the features supported by the tools by using `./pico_project.py --list`. These features can
be added to the project using the `--feature` options, this can be used multiple times.



## GUI version

The GUI version of the tool, run by adding `--gui` to the command line, uses `tkinter` to provide a platform agnostic script that will run on Linux, Mac and Windows. All the options from the command line tool are also supported in the GUI. It may be necessary to install the `python3-tk` package for GUI support on Ubuntu/Debian platforms.

The board type selects the specific board header files to be used. The generator will scan the Pico SDK boards folder for all available boards.

You can add specific features to your project by selecting them from the check boxes on the GUI. This will ensure the build system adds the appropriate code to the build, and also adds simple example code to the project showing how to use the feature. There are a number of options available, which provide the following functionality.

Pico Wireless Options | Description
----------------------|-----------
None | Do not include any Pico W libraries
Onboard LED | Only include a small library to provide access to the PicoW LED
Polled lwIP | A polled lwIP implementation library
Background lwIP | A library to run the lwIP stack in the background.

Console Options | Description
----------------|-----------
Console over UART | Enable a serial console over the UART. This is the default.
Console over USB | Enable a console over the USB. The device will act as a USB serial port. This can be used in addition to or instead of the UART option, but note that when enabled other USB functionality is not possible.


Code Options | Description
-------------| -----------
Add examples for Pico library | Example code will be generated for some of the standard library features that by default are in the build, for example, UART support and HW dividers.
Run from RAM | Usually, the build creates a binary that will be installed to the flash memory. This forces the binary to work directly from RAM.
Generate C++ | Any generated source files will use the .cpp extension.
Enable C++ exceptions | By default exceptions are not support, check this to enable. There is an impact of speed and code size.
Enable C++ RTTI | By default RTTI (Run Time type information) is not enabled, check this to enable. There is an impact of speed and code size.
Advanced  | Brings up a table allowing selection of specific board build options. These options alter the way the features work, and should be used with caution.


Build Options | Description
--------------| -----------
Run Build | Once the project has been created, build it. This will produce files ready for download to the Raspberry Pi Pico.
Overwrite Project | If a project already exists in the specified folder, overwrite it with the new project. This will overwrite any changes you may have made.

IDE Options | Description
------------| -----------
Create VSCode Project | As well as the CMake files, also create the appropriate Visual Studio Code project files.
Debugger | Use the specified debugger in the IDE









