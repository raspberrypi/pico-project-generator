#!/usr/bin/env python3

#
# Copyright (c) 2020 Raspberry Pi (Trading) Ltd.
#
# SPDX-License-Identifier: BSD-3-Clause
#

# Used to store any settings and variables needed by both the other files.

# This variable is needed to prevent import loops
LOAD_GUI = False

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

isMac = False
isWindows = False