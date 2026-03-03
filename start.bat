@echo off
setlocal

echo Starting Trade Application...
echo.

:: Start backend in a new window
echo Starting Backend (ASP.NET Core)...
start "Backend - ASP.NET Core" cmd /k "cd app && dotnet run --launch-profile http"

:: Wait a moment for backend to initialize
timeout /t 2 /nobreak >nul

:: Start frontend in a new window
echo Starting Frontend (React + Vite)...
start "Frontend - React + Vite" cmd /k "cd client && npm run dev"

echo.
echo ========================================
echo Backend running on http://localhost:5077
echo Frontend running on http://localhost:5173
echo ========================================
echo.
echo Close the terminal windows to stop the services
echo.

endlocal

@REM Made with Bob
