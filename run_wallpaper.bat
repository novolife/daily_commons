@echo off
chcp 65001 >nul
cd /d "%~dp0"
python wallpaper.py --tray %*
if errorlevel 1 pause
