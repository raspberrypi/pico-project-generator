@if not defined _echo echo off
set "lscp-path=%cd%"

rem https://stackoverflow.com/questions/22352793/reading-a-registry-value-to-a-batch-variable-handling-spaces-in-value
for /f "usebackq tokens=2,*" %%h in (
  `"reg query "HKLM\SOFTWARE\Kitware\CMake\Packages\pico-sdk-tools" 2>NUL | find /i "SDK""`
  ) do (
  set "pico-env-for-projGen-path=%%i"
)

cd /D "%pico-env-for-projGen-path%"
cd ..
set "pico-env-for-projGen-path="
call pico-env.cmd

cd /D %lscp-path%
set "lscp-path="

REM https://blog.finxter.com/how-to-find-path-where-python-is-installed-on-windows/
py.exe -c "import os, sys; print(os.path.dirname(sys.executable))" > lspver.tmp
set /p ls-pypath= < lspver.tmp
del lspver.tmp
call "%ls-pypath%\python" pico_project.py --gui
set ls-pypath=

