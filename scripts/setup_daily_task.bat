@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set ROOT=%~dp0..
set ROOT=%ROOT:~0,-1%
set PYTHON_CMD=python
set WALLPAPER_SCRIPT=%ROOT%\wallpaper.py

echo ========================================
echo   Daily Commons Wallpaper - 每日任务设置
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo 将创建每日 8:00 自动更换壁纸的任务...
echo.
schtasks /create /tn "DailyCommonsWallpaper" /tr "\"%PYTHON_CMD%\" \"%WALLPAPER_SCRIPT%\"" /sc daily /st 08:00 /f
if errorlevel 1 (
    echo [错误] 创建任务失败，请以管理员身份运行此脚本
    pause
    exit /b 1
)

echo.
echo [成功] 已创建计划任务 "DailyCommonsWallpaper"
echo 每天 8:00 将自动更换壁纸
echo.
echo 立即运行一次? (Y/N)
set /p RUN_NOW=
if /i "%RUN_NOW%"=="Y" (
    python "%WALLPAPER_SCRIPT%"
)
pause
