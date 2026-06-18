@echo off
SET VENV_NAME=ftcs
SET REQ_FILE=requirements.txt

:: 1. Check if the virtual environment folder already exists
IF EXIST "%VENV_NAME%\" (
    echo [INFO] Virtual environment '%VENV_NAME%' already exists. Skipping creation.
) ELSE (
    echo [INFO] Creating virtual environment '%VENV_NAME%'...
    python -m venv %VENV_NAME%
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to create the virtual environment. Ensure Python is installed and in your PATH.
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created.
)

:: 2. Check if requirements.txt exists before installing
IF EXIST "%REQ_FILE%" (
    echo [INFO] Installing dependencies from %REQ_FILE%...
    call %VENV_NAME%\Scripts\activate.bat && pip install -r %REQ_FILE%
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [SUCCESS] Dependencies installed successfully.
) ELSE (
    echo [WARNING] '%REQ_FILE%' not found. Skipping dependency installation.
)

:: 3. Permanently activate the venv for the current Command Prompt window
echo [INFO] Activating '%VENV_NAME%'...
call %VENV_NAME%\Scripts\activate.bat
