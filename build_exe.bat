@echo off
chcp 65001 >nul
echo ============================================
echo   梦幻西游自动脚本 - Windows 打包脚本
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

echo [1/4] 安装 PyInstaller...
pip install pyinstaller --quiet
if %errorlevel% neq 0 (
    echo [错误] PyInstaller 安装失败
    pause
    exit /b 1
)

echo [2/4] 清理旧构建...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo [3/4] 开始打包（可能需要 3-5 分钟）...
pyinstaller --onefile --windowed ^
    --name "梦幻西游自动脚本" ^
    --add-data "config;config" ^
    --add-data "core;core" ^
    --add-data "modules;modules" ^
    --add-data "templates;templates" ^
    --hidden-import cv2 ^
    --hidden-import numpy ^
    --hidden-import mss ^
    --hidden-import pyautogui ^
    --hidden-import PIL ^
    --hidden-import keyboard ^
    --hidden-import PyQt5 ^
    --hidden-import config.settings ^
    --hidden-import core.window_group ^
    --hidden-import core.screen ^
    --hidden-import core.input_sim ^
    --hidden-import core.captcha ^
    --hidden-import core.flow_control ^
    --hidden-import core.session_manager ^
    --hidden-import modules.combat ^
    --hidden-import modules.navigation ^
    --hidden-import modules.teleport ^
    --hidden-import modules.station_coach ^
    --hidden-import modules.task_reader ^
    --hidden-import modules.bandit_hunt ^
    --hidden-import modules.escort_landmark ^
    --hidden-import modules.warehouse ^
    --hidden-import modules.ocr_engine ^
    --hidden-import modules.tasks.sect_quest ^
    --hidden-import modules.tasks.ghost_hunt ^
    --hidden-import modules.tasks.treasure_map ^
    --icon NONE ^
    launcher.py

if %errorlevel% neq 0 (
    echo [错误] 打包失败，请检查错误信息
    pause
    exit /b 1
)

echo [4/4] 复制额外文件...
if not exist "dist\logs" mkdir "dist\logs"
if not exist "dist\templates" mkdir "dist\templates"

echo.
echo ============================================
echo   打包完成！
echo   输出: dist\梦幻西游自动脚本.exe
echo   复制 dist 整个文件夹到任意位置即可运行
echo ============================================
echo.
pause
