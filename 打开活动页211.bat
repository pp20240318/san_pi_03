@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PORT=8080
set URL=http://127.0.0.1:%PORT%/aba/activity/Custom/211/

if not exist "aba\activity\Custom\211\index.html" (
    echo 未找到 aba 目录，请先运行: python prepare_subfolder.py
    pause
    exit /b 1
)

echo 启动本地预览（端口 %PORT%）...
start "san_pi_03-http" /min cmd /c "cd /d "%~dp0" && python -m http.server %PORT%"
timeout /t 2 /nobreak >nul
start "" "%URL%"
echo 已打开: %URL%
pause
