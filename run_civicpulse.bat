@echo off
REM Double-click launcher for Windows - starts the CivicPulse server.
cd /d %~dp0
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
py -m uvicorn app.main:app --port 8000
pause
