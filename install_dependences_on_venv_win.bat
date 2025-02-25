@echo off

echo Checking for virtual environment...
if not exist .venv (
    echo Virtual environment not found. Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Error creating virtual environment. Please ensure Python is installed and in your PATH.
        pause
        exit /b
    )
)

call .venv\Scripts\activate
if errorlevel 1 (
    echo Error activating virtual environment.
    pause
    exit /b
)

echo Checking for required libraries...

REM Check if PyQt5 is installed
pip show PyQt5 > nul 2>&1
if errorlevel 1 (
    echo Error: PyQt5 is not installed. Installing automatically...
	pip install PyQt5
)

REM Check if google-generativeai is installed
pip show google-generativeai > nul 2>&1
if errorlevel 1 (
    echo Error: google-generativeai is not installed. Installing automatically...
	pip install google-generativeai
)

REM Optional: Check if PyQt5-tools is installed (if you need it)
pip show PyQt5-tools > nul 2>&1
if errorlevel 1 (
    echo Warning: PyQt5-tools is not installed. You may need to install it for development purposes using: pip install PyQt5-tools
    echo Continuing anyway...
    echo.
)

echo All required libraries found. Starting the application...

python src
