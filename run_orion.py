#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import getpass
import socket
import re
import time
import threading


def clear_screen():
    """Очистка экрана для разных операционных систем"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Вывод заголовка программы"""
    header = r"""
  ____        _                _    _            _     ____            
 / __ \      (_)              | |  | |          | |   / ___|           
| |  | |_ __  _  ___  _ __    | |  | | ___  _ __| | _| (___   ___  ___ 
| |  | | '_ \| |/ _ \| '_ \   | |/\| |/ _ \| '__| |/ /\___ \ / _ \/ __|
| |__| | | | | | (_) | | | |  \  /\  / (_) | |  |   < ____) |  __/ (__ 
 \____/|_| |_|_|\___/|_| |_|   \/  \/ \___/|_|  |_|\_\_____/ \___|\___|

        СИСТЕМА УПРАВЛЕНИЯ ОХРАНОЙ ТРУДА
        """
    print(header)
    print("\nПростой запуск OrionWorkSec\n")


def get_database_config():
    """Получение конфигурации базы данных от пользователя"""
    config_path = 'orion_config.json'

    # Значения по умолчанию
    config = {
        'host': 'localhost',
        'port': '5432',
        'name': 'OrionDB',
        'user': 'postgres',
        'password': ''
    }

    # Загрузка существующей конфигурации, если есть
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            print("Загружена существующая конфигурация.\n")
        except:
            print("Не удалось загрузить существующую конфигурацию, используются значения по умолчанию.\n")

    # Запрос параметров у пользователя
    print("===== НАСТРОЙКА БАЗЫ ДАННЫХ =====")
    print("Введите параметры подключения к базе данных PostgreSQL:")
    print("(Нажмите Enter, чтобы использовать значение в скобках)\n")

    config['host'] = input(f"Адрес сервера БД [{config['host']}]: ") or config['host']
    config['port'] = input(f"Порт [{config['port']}]: ") or config['port']
    config['name'] = input(f"Имя базы данных [{config['name']}]: ") or config['name']
    config['user'] = input(f"Имя пользователя БД [{config['user']}]: ") or config['user']

    # Запрос пароля с маскировкой
    pw_message = "Пароль (пусто): " if not config['password'] else "Пароль (сохранить существующий): "
    password = getpass.getpass(pw_message)
    if password:
        config['password'] = password

    # Сохранение конфигурации
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f)
        print("\nКонфигурация сохранена успешно.\n")
    except Exception as e:
        print(f"\nНе удалось сохранить конфигурацию: {e}\n")

    return config


def update_settings(config):
    """Обновление файла settings.py с параметрами БД"""
    settings_path = os.path.join('OrionWorkSec', 'settings.py')

    if not os.path.exists(settings_path):
        print(f"Ошибка: Файл settings.py не найден по пути {settings_path}")
        return False

    # Создаем резервную копию файла настроек
    backup_path = os.path.join('OrionWorkSec', 'settings.py.bak')
    try:
        with open(settings_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
        print(f"Создана резервная копия настроек: {backup_path}")
    except Exception as e:
        print(f"Предупреждение: Не удалось создать резервную копию: {e}")

    # Чтение файла настроек, пробуем разные кодировки
    encodings = ['utf-8', 'windows-1251', 'latin1', 'cp1251']
    content = None
    used_encoding = None

    for encoding in encodings:
        try:
            with open(settings_path, 'r', encoding=encoding) as f:
                content = f.read()
                used_encoding = encoding
                print(f"Файл настроек прочитан с кодировкой {encoding}")
                break
        except UnicodeDecodeError:
            continue

    if content is None:
        print("Ошибка: Не удалось прочитать файл настроек ни с одной из поддерживаемых кодировок")
        return False

    # Подготавливаем строку настроек базы данных
    db_settings = f"""
DATABASES = {{
    'default': {{
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '{config['name']}',
        'USER': '{config['user']}',
        'PASSWORD': '{config['password']}',
        'HOST': '{config['host']}',
        'PORT': '{config['port']}',
    }}
}}
"""

    # Читаем файл построчно и заменяем блок DATABASES
    with open(settings_path, 'r', encoding=used_encoding) as f:
        lines = f.readlines()

    new_lines = []
    in_database_section = False
    database_section_ended = False

    for line in lines:
        # Начало блока DATABASES
        if 'DATABASES' in line and '=' in line and '{' in line:
            in_database_section = True
            # Добавляем наш блок DATABASES
            new_lines.append(db_settings)
            continue

        # Если мы внутри блока DATABASES, пропускаем строки
        if in_database_section and not database_section_ended:
            # Если видим строку с комментарием или настройкой после DATABASES, значит блок закончился
            if line.strip().startswith('#') or ('AUTH_PASSWORD_VALIDATORS' in line):
                database_section_ended = True
                new_lines.append('\n' + line)  # Добавляем пустую строку и текущую строку
            elif line.strip() == '}' or line.strip() == '}}':
                # Пропускаем закрывающие скобки блока DATABASES
                continue
        else:
            # Если не в блоке DATABASES или блок уже закончился, добавляем строку как есть
            new_lines.append(line)

    # Записываем обновленный файл
    try:
        with open(settings_path, 'w', encoding=used_encoding) as f:
            f.writelines(new_lines)
        print("Файл настроек Django успешно обновлен.")
        return True
    except Exception as e:
        print(f"Ошибка при записи файла настроек: {e}")
        return False


def create_database(config):
    """Создание базы данных, если она не существует"""
    print("\nПроверка соединения с базой данных...")

    try:
        # Проверка существования базы данных через subprocess
        env = os.environ.copy()
        env['PGPASSWORD'] = config['password']

        # Команда для проверки базы данных
        check_cmd = [
            'psql',
            '-h', config['host'],
            '-p', config['port'],
            '-U', config['user'],
            '-d', 'postgres',
            '-c', f"SELECT 1 FROM pg_database WHERE datname = '{config['name']}'"
        ]

        result = subprocess.run(
            check_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=(os.name == 'nt')  # shell=True для Windows
        )

        if "1 row" in result.stdout:
            print(f"База данных '{config['name']}' существует.")
            return True

        # База данных не существует, создаем её
        print(f"База данных '{config['name']}' не найдена. Создание...")

        create_cmd = [
            'psql',
            '-h', config['host'],
            '-p', config['port'],
            '-U', config['user'],
            '-d', 'postgres',
            '-c', f"CREATE DATABASE \"{config['name']}\""
        ]

        create_result = subprocess.run(
            create_cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=(os.name == 'nt')
        )

        if create_result.returncode != 0:
            print(f"Ошибка при создании базы данных: {create_result.stderr}")
            return False

        print(f"База данных '{config['name']}' успешно создана.")

        # Запускаем SQL-скрипт инициализации, если он есть
        if os.path.exists('скрипт.txt'):
            print("\nИнициализация базы данных...")

            init_cmd = [
                'psql',
                '-h', config['host'],
                '-p', config['port'],
                '-U', config['user'],
                '-d', config['name'],
                '-f', 'скрипт.txt'
            ]

            init_result = subprocess.run(
                init_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=(os.name == 'nt')
            )

            if init_result.returncode != 0:
                print(f"Предупреждение: Возможно, не удалось полностью инициализировать базу данных.")
                print(f"Детали ошибки: {init_result.stderr}")
            else:
                print("База данных успешно инициализирована.")
        else:
            print("Предупреждение: Файл SQL-скрипта 'скрипт.txt' не найден для инициализации БД.")

        return True

    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")
        return False


def is_port_available(port):
    """Проверка доступности порта"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0


def find_available_port(start_port=8000, max_attempts=10):
    """Поиск доступного порта, начиная со start_port"""
    port = start_port
    attempts = 0

    while attempts < max_attempts:
        if is_port_available(port):
            return port
        port += 1
        attempts += 1

    # Если не удалось найти свободный порт, возвращаем порт по умолчанию
    return start_port


def start_django_server():
    """Запуск сервера разработки Django"""
    # Миграции перед запуском (опционально)
    print("\nПодготовка миграций Django...")

    try:
        # Применяем миграции
        migrate_cmd = [sys.executable, 'manage.py', 'migrate']
        subprocess.run(migrate_cmd, check=True, shell=(os.name == 'nt'))

        # Поиск доступного порта
        port = find_available_port()

        # Запуск сервера Django
        print(f"\nЗапуск сервера Django на порту {port}...\n")

        # Запускаем сервер
        cmd = [sys.executable, 'manage.py', 'runserver', f'0.0.0.0:{port}']

        server_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            shell=(os.name == 'nt')
        )

        # Создание потока для чтения и отображения вывода сервера
        def read_output():
            while server_process and server_process.poll() is None:
                line = server_process.stdout.readline()
                if line:
                    line = line.strip()
                    print(f"[Django] {line}")

            if server_process:
                # Чтение оставшегося вывода
                remaining_output = server_process.stdout.read()
                if remaining_output:
                    for line in remaining_output.strip().split('\n'):
                        print(f"[Django] {line}")

        # Запуск потока чтения вывода
        output_thread = threading.Thread(target=read_output)
        output_thread.daemon = True
        output_thread.start()

        # Ожидание запуска сервера
        time.sleep(2)

        if server_process.poll() is not None:
            print("\nОшибка: Не удалось запустить сервер. Проверьте логи для получения деталей.")
            return False

        print("\n===== СЕРВЕР ЗАПУЩЕН =====")
        print(f"Приложение доступно по адресу: http://localhost:{port}/")
        print("Нажмите Ctrl+C для остановки сервера")

        try:
            # Поддержание работы скрипта
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nОстановка сервера...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("Сервер не остановился в течение 5 секунд, принудительное завершение...")
                server_process.kill()

            print("Сервер остановлен.")

        return True
    except Exception as e:
        print(f"Ошибка при запуске сервера Django: {e}")
        return False


def main():
    """Основная функция запуска"""
    # Очистка экрана
    clear_screen()

    # Вывод заголовка
    print_header()

    # Переходим в каталог скрипта для корректной работы с относительными путями
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Проверка наличия manage.py
    if not os.path.exists('manage.py'):
        print("Ошибка: Файл manage.py не найден. Убедитесь, что вы запускаете скрипт из корневой директории проекта.")
        input("Нажмите Enter для выхода...")
        return

    # Получение конфигурации базы данных
    db_config = get_database_config()

    # Обновление файла настроек Django
    if not update_settings(db_config):
        print("\nНе удалось обновить настройки Django. Проверьте права доступа к файлам.")
        input("Нажмите Enter для выхода...")
        return

    # Проверка и создание базы данных
    if not create_database(db_config):
        print("\nВозникли проблемы при настройке базы данных.")
        choice = input("Продолжить запуск сервера без настройки базы данных? (y/n): ")
        if choice.lower() != 'y':
            input("Нажмите Enter для выхода...")
            return

    # Запуск сервера Django
    start_django_server()

    input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()