@echo off
chcp 65001 >nul
echo ========================================
echo  MONOTAL Server Start
echo ========================================
echo.
echo  http://0.0.0.0:8000 でアクセス可能
echo  Ctrl+C で停止
echo ========================================
python manage.py runserver 0.0.0.0:8000
pause
