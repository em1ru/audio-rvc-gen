@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  Golden Dataset — Portable Python 3.10 Bootstrap
::  Run from project root:  scripts\setup_env.bat
:: ============================================================

:: Resolve ROOT as the parent of scripts\
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%I in ("%SCRIPT_DIR%\..") do set "ROOT=%%~fI"

set "PY_DIR=%ROOT%\py"
set "PYTHON=%PY_DIR%\python.exe"
set "PIP=%PY_DIR%\Scripts\pip.exe"
set "PY_ZIP=python-3.10.11-embed-amd64.zip"
set "PY_URL=https://www.python.org/ftp/python/3.10.11/%PY_ZIP%"
set "GETPIP_URL=https://bootstrap.pypa.io/get-pip.py"

echo.
echo ============================================================
echo   Golden Dataset — Environment Bootstrap
echo ============================================================
echo   Root: %ROOT%
echo ============================================================
echo.

:: --------------------------------------------------
:: Step 1: Download Python 3.10 Embeddable
:: --------------------------------------------------
if exist "%PYTHON%" (
    echo [OK] Python already found at %PYTHON%
    goto :install_pip
)

echo [1/5] Downloading Python 3.10.11 Embeddable...
if not exist "%PY_DIR%" mkdir "%PY_DIR%"

curl -L -o "%PY_DIR%\%PY_ZIP%" "%PY_URL%"
if errorlevel 1 (
    echo [ERROR] Failed to download Python. Check your internet connection.
    pause
    exit /b 1
)

echo [1/5] Extracting Python...
powershell -Command "Expand-Archive -Path '%PY_DIR%\%PY_ZIP%' -DestinationPath '%PY_DIR%' -Force"
if errorlevel 1 (
    echo [ERROR] Failed to extract Python zip.
    pause
    exit /b 1
)
del "%PY_DIR%\%PY_ZIP%" 2>nul

:: --------------------------------------------------
:: Step 2: Enable import site in ._pth file
:: --------------------------------------------------
echo [2/5] Enabling import site...
set "PTH_FILE=%PY_DIR%\python310._pth"
if exist "%PTH_FILE%" (
    powershell -Command "(Get-Content '%PTH_FILE%') -replace '#import site','import site' | Set-Content '%PTH_FILE%'"
    echo [OK] import site enabled in python310._pth
) else (
    echo [WARN] _pth file not found — site packages may not work correctly.
)

:: --------------------------------------------------
:: Step 3: Install pip
:: --------------------------------------------------
:install_pip
if exist "%PIP%" (
    echo [OK] pip already installed.
    goto :install_packages
)

echo [3/5] Installing pip...
curl -L -o "%PY_DIR%\get-pip.py" "%GETPIP_URL%"
if errorlevel 1 (
    echo [ERROR] Failed to download get-pip.py.
    pause
    exit /b 1
)
"%PYTHON%" "%PY_DIR%\get-pip.py" --no-warn-script-location
if errorlevel 1 (
    echo [ERROR] pip installation failed.
    pause
    exit /b 1
)
del "%PY_DIR%\get-pip.py" 2>nul
echo [OK] pip installed.

:: --------------------------------------------------
:: Step 4: Install PyTorch (CPU-only)
:: --------------------------------------------------
:install_packages
echo.
echo [4/5] Installing PyTorch (CPU-only)...
"%PYTHON%" -m pip install --no-warn-script-location ^
    torch torchvision torchaudio ^
    --index-url https://download.pytorch.org/whl/cpu

if errorlevel 1 (
    echo [ERROR] PyTorch installation failed.
    pause
    exit /b 1
)
echo [OK] PyTorch CPU installed.

:: --------------------------------------------------
:: Step 5: Install RVC + dependencies
:: --------------------------------------------------
echo.
echo [5/5] Installing rvc-python and dependencies...
"%PYTHON%" -m pip install --no-warn-script-location ^
    rvc-python ^
    librosa ^
    faiss-cpu ^
    pydub ^
    scipy ^
    soundfile ^
    pyyaml

if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)
echo [OK] All dependencies installed.

:: --------------------------------------------------
:: Validation
:: --------------------------------------------------
echo.
echo ============================================================
echo   Validating installation...
echo ============================================================
"%PYTHON%" -c "import torch; import rvc_python; import librosa; import faiss; import pydub; import scipy; import soundfile; import yaml; print('[OK] All imports successful. torch=' + torch.__version__)"
if errorlevel 1 (
    echo [ERROR] Validation failed — some imports are broken.
    pause
    exit /b 1
)

:: --------------------------------------------------
:: Create directory structure
:: --------------------------------------------------
echo.
echo [OK] Creating directory structure...
if not exist "%ROOT%\models" mkdir "%ROOT%\models"
if not exist "%ROOT%\data\real" mkdir "%ROOT%\data\real"
if not exist "%ROOT%\data\fake" mkdir "%ROOT%\data\fake"

echo.
echo ============================================================
echo   SUCCESS! Environment is ready.
echo   Python: %PYTHON%
echo   Pip:    %PIP%
echo ============================================================
echo.
echo Next steps:
echo   1. Place voice models in: %ROOT%\models\^<voice_name^>\
echo   2. Extract corpus:  "%PYTHON%" "%ROOT%\scripts\extract_corpus.py"
echo   3. Run pipeline:    "%PYTHON%" "%ROOT%\run_pipeline.py" --list-models
echo   4. Run inference:   "%PYTHON%" "%ROOT%\run_pipeline.py" --full
echo.
pause
