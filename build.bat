@echo off
echo Building Criminal Detection System Executable...
echo This may take several minutes, please wait...
echo.

cd /d "%~dp0"
pyinstaller build_executable.spec

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo Build completed successfully!
    echo ========================================
    echo Your executable is located in: dist\CriminalDetectionSystem.exe
    echo.
    echo You can now distribute this .exe file to others.
    echo.
) else (
    echo.
    echo Build failed. Please check the error messages above.
    pause
)

pause
