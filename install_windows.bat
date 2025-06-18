@echo off
echo ===================================================
echo      Установщик OrionWorkSec для Windows
echo ===================================================

:: Проверка, установлен ли Python
python --version > nul 2>&1
if errorlevel 1 (
    echo Python не установлен или отсутствует в PATH.
    echo Пожалуйста, установите Python 3.8 или выше и повторите попытку.
    pause
    exit /b
)

:: Запуск скрипта установки
echo.
echo Запуск скрипта установки...
python setup.py
if errorlevel 1 (
    echo Установка не удалась. Проверьте сообщения об ошибках выше.
    pause
    exit /b
)

:: Если установка прошла успешно, запустить лаунчер
echo.
echo Установка успешно завершена!
echo.
echo Нажмите любую клавишу для запуска приложения...
pause > nul

echo.
echo Запуск OrionWorkSec...
python orion_launcher.py

pause