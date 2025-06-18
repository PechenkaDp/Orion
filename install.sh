#!/bin/bash

echo "==================================================="
echo "      Установщик OrionWorkSec для Linux/macOS"
echo "==================================================="

# Проверка, установлен ли Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 не установлен или отсутствует в PATH."
    echo "Пожалуйста, установите Python 3.8 или выше и повторите попытку."
    exit 1
fi

# Сделать скрипт лаунчера исполняемым
chmod +x orion_launcher.py

# Запуск скрипта установки
echo
echo "Запуск скрипта установки..."
python3 setup.py
if [ $? -ne 0 ]; then
    echo "Установка не удалась. Проверьте сообщения об ошибках выше."
    exit 1
fi

# Если установка прошла успешно, запустить лаунчер
echo
echo "Установка успешно завершена!"
echo
echo "Нажмите Enter для запуска приложения..."
read

echo
echo "Запуск OrionWorkSec..."
python3 orion_launcher.py