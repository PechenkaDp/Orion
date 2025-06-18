from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Department, Employee, InstructionType, PPEItem, Hazard

class Command(BaseCommand):
    help = 'Initialize basic data for the application'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data initialization...'))

        # Создание суперпользователя
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@orion.com',
                password='123',
                first_name='Админ',
                last_name='Системы'
            )
            self.stdout.write(self.style.SUCCESS('Admin user created'))
        else:
            admin_user = User.objects.get(username='admin')
            self.stdout.write(self.style.WARNING('Admin user already exists'))

        # Создание подразделений
        departments_data = [
            'Администрация',
            'Отдел охраны труда',
            'Производственный цех №1',
            'Склад',
            'ИТ-отдел',
            'Бухгалтерия'
        ]

        for dept_name in departments_data:
            dept, created = Department.objects.get_or_create(
                name=dept_name,
                defaults={'description': f'Подразделение {dept_name}'}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Department "{dept_name}" created'))

        # Создание профиля сотрудника для админа
        admin_dept = Department.objects.get(name='Администрация')
        if not hasattr(admin_user, 'employee'):
            Employee.objects.create(
                user=admin_user,
                department=admin_dept,
                position='Системный администратор',
                role='admin',
                hire_date='2024-01-01'
            )
            self.stdout.write(self.style.SUCCESS('Admin employee profile created'))

        # Создание типов инструктажей
        instruction_types = [
            ('Вводный инструктаж', 'Проводится для всех вновь принимаемых на работу', None),
            ('Первичный инструктаж', 'Проводится на рабочем месте до начала работы', None),
            ('Повторный инструктаж', 'Периодический инструктаж для всех работников', 180),
            ('Целевой инструктаж', 'Проводится перед выполнением разовых работ', None),
            ('Внеплановый инструктаж', 'При изменении технологии или после происшествий', None),
        ]

        for name, description, period in instruction_types:
            InstructionType.objects.get_or_create(
                name=name,
                defaults={'description': description, 'period_days': period}
            )

        # Создание базовых СИЗ
        ppe_items = [
            ('Защитная каска', 'Защитная каска для строительных работ', 'Защита головы', 730),
            ('Защитные очки', 'Очки для защиты глаз', 'Защита глаз', 365),
            ('Респиратор', 'Респиратор для защиты органов дыхания', 'Защита органов дыхания', 90),
            ('Защитные перчатки', 'Перчатки для работы с химикатами', 'Защита рук', 30),
            ('Защитная обувь', 'Обувь со стальным носком', 'Защита ног', 365),
        ]

        for name, description, category, period in ppe_items:
            PPEItem.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'category': category,
                    'standard_issue_period': period
                }
            )

        # Создание базовых опасностей
        hazards = [
            ('Падение с высоты', 'Риск падения при работе на высоте', 'Физические опасности'),
            ('Химические вещества', 'Воздействие опасных химических веществ', 'Химические опасности'),
            ('Поражение электрическим током', 'Риск поражения электрическим током', 'Электрические опасности'),
            ('Движущиеся механизмы', 'Опасность от движущихся частей оборудования', 'Механические опасности'),
            ('Шум', 'Повышенный уровень шума', 'Физические опасности'),
        ]

        for name, description, category in hazards:
            Hazard.objects.get_or_create(
                name=name,
                defaults={'description': description, 'category': category}
            )

        self.stdout.write(self.style.SUCCESS('Data initialization completed successfully!'))
        self.stdout.write(self.style.SUCCESS('Admin credentials: admin / 123'))