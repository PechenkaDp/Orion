from django.db import migrations, transaction
from django.contrib.auth.hashers import make_password


def create_initial_data(apps, schema_editor):
    """Создание начальных данных из SQL скрипта"""

    # Получаем модели
    Department = apps.get_model('core', 'Department')
    User = apps.get_model('auth', 'User')
    Employee = apps.get_model('core', 'Employee')
    PPEItem = apps.get_model('core', 'PPEItem')
    InstructionType = apps.get_model('core', 'InstructionType')
    Hazard = apps.get_model('core', 'Hazard')

    with transaction.atomic():
        # Создаем подразделения
        departments_data = [
            ('Администрация', 'Руководство компании'),
            ('Отдел охраны труда', 'Специалисты по охране труда'),
            ('Производственный цех №1', 'Основной производственный цех'),
            ('Склад', 'Складские помещения'),
            ('ИТ-отдел', 'Отдел информационных технологий'),
            ('Бухгалтерия', 'Финансовый отдел'),
        ]

        departments = []
        for name, description in departments_data:
            dept, created = Department.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            departments.append(dept)

        # Создаем пользователей (только если их нет)
        users_data = [
            ('admin', 'admin@example.com', 'Админ', 'Админов'),
            ('safety_specialist', 'safety@example.com', 'Иван', 'Петров'),
            ('department_head', 'head@example.com', 'Мария', 'Сидорова'),
            ('employee1', 'emp1@example.com', 'Алексей', 'Иванов'),
            ('employee2', 'emp2@example.com', 'Ольга', 'Смирнова'),
            ('medical', 'medical@example.com', 'Елена', 'Врачева'),
            ('technician', 'tech@example.com', 'Сергей', 'Мастеров'),
        ]

        # Пароль для всех тестовых пользователей: admin123
        hashed_password = make_password('admin123')

        users = []
        for username, email, first_name, last_name in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'password': hashed_password,
                    'is_active': True,
                }
            )
            users.append(user)

        # Делаем первого пользователя суперпользователем
        if users:
            users[0].is_superuser = True
            users[0].is_staff = True
            users[0].save()

        # Создаем Employee записи
        employees_data = [
            (0, 0, 'Генеральный директор', 'admin', '2020-01-01'),
            (1, 1, 'Специалист по охране труда', 'safety_specialist', '2021-03-15'),
            (2, 2, 'Начальник цеха', 'department_head', '2020-05-20'),
            (3, 2, 'Оператор станка', 'employee', '2022-02-10'),
            (4, 3, 'Кладовщик', 'employee', '2022-07-01'),
            (5, 0, 'Медицинский работник', 'medical_worker', '2021-09-12'),
            (6, 4, 'Техник-специалист', 'technician', '2023-01-15'),
        ]

        for user_idx, dept_idx, position, role, hire_date in employees_data:
            if user_idx < len(users) and dept_idx < len(departments):
                Employee.objects.get_or_create(
                    user=users[user_idx],
                    defaults={
                        'department': departments[dept_idx],
                        'position': position,
                        'role': role,
                        'hire_date': hire_date,
                    }
                )

        # Создаем СИЗ
        ppe_items_data = [
            ('Защитная каска', 'Защитная каска для строительных работ', 'Защита головы', 730),
            ('Защитные очки', 'Очки для защиты глаз', 'Защита глаз', 365),
            ('Респиратор', 'Респиратор для защиты органов дыхания', 'Защита органов дыхания', 90),
            ('Защитные перчатки', 'Перчатки для работы с химикатами', 'Защита рук', 30),
            ('Защитная обувь', 'Обувь со стальным носком', 'Защита ног', 365),
        ]

        for name, description, category, period in ppe_items_data:
            PPEItem.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'category': category,
                    'standard_issue_period': period,
                }
            )

        # Создаем типы инструктажей
        instruction_types_data = [
            ('Вводный инструктаж', 'Проводится для всех вновь принимаемых на работу', None),
            ('Первичный инструктаж', 'Проводится на рабочем месте до начала работы', None),
            ('Повторный инструктаж', 'Периодический инструктаж для всех работников', 180),
            ('Целевой инструктаж', 'Проводится перед выполнением разовых работ', None),
            ('Внеплановый инструктаж', 'При изменении технологии или после происшествий', None),
        ]

        for name, description, period_days in instruction_types_data:
            InstructionType.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'period_days': period_days,
                }
            )

        # Создаем опасности
        hazards_data = [
            ('Падение с высоты', 'Риск падения при работе на высоте', 'Физические опасности'),
            ('Химические вещества', 'Воздействие опасных химических веществ', 'Химические опасности'),
            ('Поражение электрическим током', 'Риск поражения электрическим током', 'Электрические опасности'),
            ('Движущиеся механизмы', 'Опасность от движущихся частей оборудования', 'Механические опасности'),
            ('Шум', 'Повышенный уровень шума', 'Физические опасности'),
            ('Вибрация', 'Повышенный уровень вибрации', 'Физические опасности'),
            ('Недостаточное освещение', 'Плохая видимость на рабочем месте', 'Физические опасности'),
            ('Повышенная температура', 'Работа при высоких температурах', 'Физические опасности'),
        ]

        for name, description, category in hazards_data:
            Hazard.objects.get_or_create(
                name=name,
                defaults={
                    'description': description,
                    'category': category,
                }
            )


def reverse_initial_data(apps, schema_editor):
    """Откат миграции - удаление начальных данных"""
    # В случае отката можно удалить созданные данные
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_initial_data, reverse_initial_data),
    ]