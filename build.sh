#!/bin/bash

# Установка зависимостей
pip install -r requirements.txt

# Применение миграций
python manage.py migrate --verbosity=2

# Создание суперпользователя (опционально)
# python manage.py shell -c "
# from django.contrib.auth.models import User;
# User.objects.filter(username='admin').exists() or \
# User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
# "

# Сбор статических файлов
python manage.py collectstatic --noinput --clear

echo "Build completed successfully!"