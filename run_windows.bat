@echo off
echo ===================================================
echo      Запуск OrionWorkSec для Windows
echo ===================================================

:: Переход в директорию скрипта
cd /d "%~dp0"

:: Проверка, установлен ли Python
python --version > nul 2>&1
if errorlevel 1 (
    echo Python не установлен или отсутствует в PATH.
    echo Пожалуйста, установите Python 3.8 или выше и повторите попытку.
    pause
    exit /b
)

:: Проверка наличия необходимых модулей
python -c "import django" > nul 2>&1
if errorlevel 1 (
    echo Установка Django...
    pip install django
    if errorlevel 1 (
        echo Не удалось установить Django.
        pause
        exit /b
    )
)

python -c "import psycopg2" > nul 2>&1
if errorlevel 1 (
    echo Установка psycopg2-binary...
    pip install psycopg2-binary
    if errorlevel 1 (
        echo Не удалось установить psycopg2-binary.
        pause
        exit /b
    )
)

echo.
echo Запуск OrionWorkSec...
echo.

:: Явно указываем интерпретатор Python и путь к скрипту
python "%~dp0run_orion.py"

:: Если скрипт завершится с ошибкой, покажем сообщение
if errorlevel 1 (
    echo Произошла ошибка при запуске приложения.
    echo Проверьте наличие всех файлов проекта и настройки PostgreSQL.
)

pause