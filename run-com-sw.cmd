@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=C:\Users\zhugu\AppData\Local\Programs\Python\Python312\python.exe"

if exist "%PYTHON_EXE%" (
    "%PYTHON_EXE%" "%SCRIPT_DIR%main.py"
    goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3.12 "%SCRIPT_DIR%main.py"
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%SCRIPT_DIR%main.py"
    goto :eof
)

echo Could not find a usable Python interpreter.
echo Expected: %PYTHON_EXE%
pause
