@echo off
cd /d "%~dp0"
"%~dp0python.exe" "%~dp0notebook.py"
if errorlevel 1 pause
