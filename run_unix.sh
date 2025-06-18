#!/bin/bash

echo "==================================================="
echo "      Запуск OrionWorkSec для Linux/macOS"
echo "==================================================="

# Проверка, установлен ли Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 не установлен или отсутствует в PATH."
    echo "Пожалуйста, установите Python 3.8 или выше и повторите попытку."
    exit 1
fi

# Проверка наличия PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "ВНИМАНИЕ: PostgreSQL не найден в системе или отсутствует в PATH."
    echo "Для работы с базой данных потребуется установить PostgreSQL."
    echo
    read -p "Хотите продолжить? (y/n): " choice
    if [[ ! "$choice" =~ ^[Yy]$ ]]; then
        echo "Установка прервана."
        exit 1
    fi
fi

# Проверка наличия необходимых модулей
if ! python3 -c "import django" &> /dev/null; then
    echo "Установка необходимых модулей Python..."
    pip3 install django psycopg2-binary
    if [ $? -ne 0 ]; then
        echo "Не удалось установить необходимые модули."
        exit 1
    fi
fi

# Делаем скрипт запуска исполняемым
chmod +x run_orion.py

# Запуск простого скрипта запуска
echo
echo "Запуск OrionWorkSec..."
python3 run_orion.py