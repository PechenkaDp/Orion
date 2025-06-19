#!/bin/bash

# Выводим информацию о подключении к БД для отладки
echo "DATABASE_URL: $DATABASE_URL"
echo "Starting Django application..."

# Ждем доступности базы данных
echo "Waiting for database..."
python -c "
import os
import time
import psycopg2
from urllib.parse import urlparse

db_url = os.environ.get('DATABASE_URL')
if db_url:
    result = urlparse(db_url)
    for i in range(30):
        try:
            conn = psycopg2.connect(
                database=result.path[1:],
                user=result.username,
                password=result.password,
                host=result.hostname,
                port=result.port
            )
            conn.close()
            print('Database is ready!')
            break
        except:
            print(f'Attempt {i+1}: Database not ready, waiting...')
            time.sleep(2)
    else:
        print('Could not connect to database after 30 attempts')
        exit(1)
"

# Применяем миграции
echo "Applying migrations..."
python manage.py migrate --verbosity=2

# Создаем суперпользователя если его нет
echo "Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

# Собираем статические файлы
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Запускаем сервер
echo "Starting server..."
exec gunicorn OrionWorkSec.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120