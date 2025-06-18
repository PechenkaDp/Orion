# Хотя сигналы будут работать при любом сохранении сотрудника или медосмотра,
# стоит также добавить периодическую задачу, которая будет проверять медосмотры регулярно.
# Для этого можно использовать Django Celery или django-crontab.

# Пример настройки django-crontab:
# 1. Установите пакет: pip install django-crontab
# 2. Добавьте 'django_crontab' в INSTALLED_APPS в settings.py
# 3. Создайте файл с задачами cron_jobs.py:

# core/cron_jobs.py
from django.utils import timezone
from datetime import timedelta
from .models import Employee, Notification
from .signals import notify_medical_workers


def check_medical_exams():
    """
    Периодическая проверка состояния медицинских осмотров всех сотрудников.
    Запускается автоматически по расписанию cron.
    """
    current_date = timezone.now().date()
    warning_date = current_date + timedelta(days=5)

    # Сотрудники с просроченными медосмотрами
    overdue_employees = Employee.objects.filter(
        next_medical_exam_date__lt=current_date
    )

    # Сотрудники с приближающимися медосмотрами
    upcoming_employees = Employee.objects.filter(
        next_medical_exam_date__gte=current_date,
        next_medical_exam_date__lte=warning_date
    )

    # Счетчики для статистики
    overdue_count = 0
    upcoming_count = 0

    # Обрабатываем просроченные медосмотры
    for employee in overdue_employees:
        # Проверяем, не было ли уже уведомления за последние 7 дней
        recent_notification = Notification.objects.filter(
            user=employee.user,
            notification_type='medical',
            created_at__gte=timezone.now() - timedelta(days=7)
        ).exists()

        if not recent_notification:
            # Создаем уведомление для сотрудника
            Notification.objects.create(
                user=employee.user,
                title='Медицинский осмотр просрочен',
                message='Ваш медицинский осмотр просрочен. Пожалуйста, обратитесь в медицинский отдел для согласования даты.',
                notification_type='medical',
                related_entity_type='employee',
                related_entity_id=employee.id,
                is_read=False
            )
            overdue_count += 1

    # Обрабатываем приближающиеся медосмотры
    for employee in upcoming_employees:
        # Проверяем, не было ли уже уведомления за последние 3 дня
        recent_notification = Notification.objects.filter(
            user=employee.user,
            notification_type='medical_warning',
            created_at__gte=timezone.now() - timedelta(days=3)
        ).exists()

        if not recent_notification:
            days_left = (employee.next_medical_exam_date - current_date).days

            # Создаем уведомление для сотрудника
            Notification.objects.create(
                user=employee.user,
                title='Приближается медицинский осмотр',
                message=f'Ваш медицинский осмотр назначен через {days_left} дней. Пожалуйста, не забудьте посетить медицинский отдел.',
                notification_type='medical_warning',
                related_entity_type='employee',
                related_entity_id=employee.id,
                is_read=False
            )
            upcoming_count += 1

    if overdue_count > 0:
        notify_medical_workers(
            'Сводка просроченных медосмотров',
            f'В системе {overdue_count} сотрудников с просроченными медосмотрами. Требуется ваше внимание.',
            'medical_overdue_summary'
        )

    if upcoming_count > 0:
        notify_medical_workers(
            'Сводка приближающихся медосмотров',
            f'В системе {upcoming_count} сотрудников с медосмотрами в ближайшие 5 дней.',
            'medical_upcoming_summary'
        )

    return f"Processed: {overdue_count} overdue and {upcoming_count} upcoming exams."
# python manage.py crontab add