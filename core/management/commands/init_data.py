from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Department, Employee


class Command(BaseCommand):
    help = 'Initialize basic data'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@orion.com',
                password='admin123',
                first_name='Админ',
                last_name='Системы'
            )

            dept, _ = Department.objects.get_or_create(
                name='Администрация',
                defaults={'description': 'Административное подразделение'}
            )

            Employee.objects.create(
                user=admin,
                department=dept,
                position='Системный администратор',
                role='admin',
                hire_date='2024-01-01'
            )

            self.stdout.write(self.style.SUCCESS('Админ создан: admin / admin123'))
        else:
            self.stdout.write(self.style.SUCCESS('Админ уже существует'))