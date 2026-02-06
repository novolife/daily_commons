@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   Daily Commons Wallpaper - 打包 EXE
echo ========================================
echo.

pip install pystray Pillow pyinstaller -q
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo.
echo 若提示 typing 包冲突，请先执行: pip uninstall typing
echo.
echo 正在打包...
pyinstaller --clean build.spec || exit /b 1
if errorlevel 1 (
    echo.
    echo [错误] 打包失败。若与 typing 冲突，请执行: pip uninstall typing
    pause
    exit /b 1
)

echo.
echo [成功] 已生成: dist\DailyCommonsWallpaper.exe
echo.
pause
