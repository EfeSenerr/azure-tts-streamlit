@echo off
echo Starting Azure TTS Web Application...
echo.
echo The application will be available at:
echo   - Local: http://localhost:5000
echo   - Network: http://%COMPUTERNAME%:5000
echo.

REM Get the local IP address
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /i "IPv4"') do (
    for /f "tokens=1" %%j in ("%%i") do (
        echo   - IP: http://%%j:5000
        goto :found
    )
)
:found

echo.
echo Press Ctrl+C to stop the server
echo.

python web_tts_app.py
