@echo off
setlocal

REM ============================================================
REM  MC Portal build script (python-minifier + PyInstaller)
REM  Both tools are already known to work on this machine.
REM  Run this from the same folder as mc_portal.py and icon.ico.
REM ============================================================

echo.
echo [1/4] Checking for Python...
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found on PATH. Install Python first, then re-run this script.
    pause
    exit /b 1
)

echo.
echo [2/4] Installing / upgrading python-minifier...
python -m pip install --upgrade python-minifier
if errorlevel 1 (
    echo ERROR: Failed to install python-minifier. Check your internet connection / pip setup.
    pause
    exit /b 1
)

echo.
echo [3/4] Obfuscating mc_portal.py...
if exist obfuscated rmdir /s /q obfuscated
mkdir obfuscated
python -m python_minifier --rename-globals --remove-literal-statements mc_portal.py > obfuscated\mc_portal.py
if errorlevel 1 (
    echo ERROR: Obfuscation failed. Scroll up for details.
    pause
    exit /b 1
)
copy icon.ico obfuscated\icon.ico >nul

echo.
echo [4/4] Packaging with PyInstaller...
cd obfuscated
python -m PyInstaller --onefile --noconsole --icon=icon.ico --name "MC Portal" mc_portal.py
cd ..

echo.
echo ============================================================
echo  BUILD COMPLETE
echo  Your compiled app is at: obfuscated\dist\MC Portal.exe
echo  Test it before distributing.
echo ============================================================
pause
