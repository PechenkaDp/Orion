from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Department, Employee


class Command(BaseCommand):
    help = 'Initialize basic data'

    def handle(self, *args, **options):
        try:
            # Создаем суперпользователя только если его нет
            if not User.objects.filter(username='admin').exists():
                admin = User.objects.create_superuser(
                    username='admin',
                    email='admin@orion.com',
                    password='admin123',
                    first_name='Админ',
                    last_name='Системы'
                )

                # Создаем базовое подразделение
                dept, created = Department.objects.get_or_create(
                    name='Администрация',
                    defaults={'description': 'Административное подразделение'}
                )

                # Создаем Employee для админа
                Employee.objects.get_or_create(
                    user=admin,
                    defaults={
                        'department': dept,
                        'position': 'Системный администратор',
                        'role': 'admin',
                        'hire_date': '2024-01-01'
                    }
                )

                self.stdout.write(
                    self.style.SUCCESS('Админ создан: admin / admin123')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('Админ уже существует')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при создании данных: {e}')
            )