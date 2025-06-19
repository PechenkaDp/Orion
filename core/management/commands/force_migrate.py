from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Force migration and create initial data'

    def handle(self, *args, **options):
        self.stdout.write('Starting forced migration...')

        # Проверяем существование таблиц
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'auth_user';
            """)
            tables = cursor.fetchall()

            if not tables:
                self.stdout.write('Tables do not exist, running migrations...')

                # Запускаем миграции
                try:
                    call_command('migrate', '--run-syncdb', verbosity=2)
                    self.stdout.write(
                        self.style.SUCCESS('Migrations completed successfully')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Migration failed: {e}')
                    )
                    return
            else:
                self.stdout.write('Tables already exist')

        # Создаем суперпользователя если его нет
        try:
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser(
                    username='admin',
                    email='admin@orion.com',
                    password='admin123',
                    first_name='Админ',
                    last_name='Системы'
                )
                self.stdout.write(
                    self.style.SUCCESS('Superuser created: admin/admin123')
                )
            else:
                self.stdout.write('Superuser already exists')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {e}')
            )

        # Запускаем создание начальных данных
        try:
            call_command('init_data')
            self.stdout.write(
                self.style.SUCCESS('Initial data created')
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not create initial data: {e}')
            )

        self.stdout.write(
            self.style.SUCCESS('Force migration completed')
        )