@if not defined _echo echo off
rem save path of the launcher script
set "lscp-path=%cd%"

rem https://stackoverflow.com/questions/22352793/reading-a-registry-value-to-a-batch-variable-handling-spaces-in-value
rem Find Regkey of Raspberry Pi Pico SDK
for /f "usebackq tokens=1,*" %%h in (
  `"reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /f "Raspberry Pi Pico SDK" 2>NUL | find /i "Raspberry Pi Pico SDK""`
  ) do (
  set "pico-sdk-regkey=%%h %%i"
)

rem Find path to Raspberry Pi Pico SDK
for /f "usebackq tokens=2,*" %%h in (
  `"reg query "%pico-sdk-regkey%" /v "InstallPath" 2>NUL"`
  ) do (
  set "pico-env-for-projGen-path=%%i"
)

rem Delete no longer required variable
set pico-sdk-regkey=

rem change directory to prepare the environment by launching the existing script pico-env
cd /D "%pico-env-for-projGen-path%"
rem Delete no longer required variable
set "pico-env-for-projGen-path="
call pico-env.cmd

rem change directory back to launcher script
cd /D %lscp-path%

rem Delete no longer required variable
set "lscp-path="

REM https://blog.finxter.com/how-to-find-path-where-python-is-installed-on-windows/
for /f "usebackq tokens=2,*" %%h in (
  `py.exe -c "import os, sys; print('Python Path ' + os.path.dirname(sys.executable))"`
  ) do (
  set "ls-pypath=%%i"
)

call "%ls-pypath%\python" pico_project.py --gui
rem Delete no longer required variable
set ls-pypath=
