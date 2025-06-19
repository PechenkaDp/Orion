from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Department, Employee
from django.utils import timezone


class Command(BaseCommand):
    help = 'Initialize basic data for the application'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data initialization...'))

        # Создаем базовые подразделения
        departments_data = [
            ('Администрация', 'Руководство компании'),
            ('Отдел охраны труда', 'Специалисты по охране труда'),
            ('Производственный цех №1', 'Основной производственный цех'),
            ('Склад', 'Складские помещения'),
            ('ИТ-отдел', 'Отдел информационных технологий'),
        ]

        for dept_name, dept_desc in departments_data:
            dept, created = Department.objects.get_or_create(
                name=dept_name,
                defaults={'description': dept_desc}
            )
            if created:
                self.stdout.write(f'Created department: {dept_name}')

        # Создаем администратора если его нет
        admin_username = 'admin'
        admin_email = 'admin@orion.ru'
        admin_password = '123'

        if not User.objects.filter(username=admin_username).exists():
            admin_user = User.objects.create_superuser(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                first_name='Администратор',
                last_name='Системы'
            )

            # Создаем профиль сотрудника для администратора
            admin_dept = Department.objects.get(name='Администрация')
            Employee.objects.create(
                user=admin_user,
                department=admin_dept,
                position='Системный администратор',
                role='admin',
                hire_date=timezone.now().date()
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Created admin user: {admin_username} / {admin_password} / {admin_email}'
                )
            )
        else:
            # Если пользователь существует, но нужно обновить пароль
            admin_user = User.objects.get(username=admin_username)
            admin_user.set_password(admin_password)
            admin_user.email = admin_email
            admin_user.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Updated admin user: {admin_username} / {admin_password} / {admin_email}'
                )
            )

        # Создаем специалиста по охране труда если его нет
        if not User.objects.filter(username='safety').exists():
            safety_user = User.objects.create_user(
                username='safety',
                email='safety@orion.com',
                password='safety123',
                first_name='Иван',
                last_name='Безопасности'
            )

            safety_dept = Department.objects.get(name='Отдел охраны труда')
            Employee.objects.create(
                user=safety_user,
                department=safety_dept,
                position='Специалист по охране труда',
                role='safety_specialist',
                hire_date=timezone.now().date()
            )

            self.stdout.write(
                self.style.SUCCESS(
                    'Created safety specialist: safety / safety123'
                )
            )
        else:
            self.stdout.write('Safety specialist already exists')

        self.stdout.write(
            self.style.SUCCESS('Data initialization completed successfully!')
        )