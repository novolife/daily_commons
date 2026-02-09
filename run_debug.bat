@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   Daily Commons Wallpaper - 调试模式
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

echo 正在以 Python 运行（显示控制台以便查看错误）...
echo.
python wallpaper.py --tray %*
echo.
echo 退出码: %errorlevel%
pause
