from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from OrionWorkSec import settings
from .models import Employee, MedicalExamination, Notification
from django.contrib.auth.models import User


@receiver(post_save, sender=Employee)
def check_medical_exam_date(sender, instance, created, **kwargs):
    """
    Сигнал, отслеживающий изменения дат медицинских осмотров сотрудников.
    Создает уведомления при просроченных или приближающихся медосмотрах.
    """
    # Текущая дата
    current_date = timezone.now().date()

    # Дата предупреждения (5 дней до медосмотра)
    warning_date = current_date + timedelta(days=5)

    # Проверяем, есть ли дата следующего медосмотра
    if instance.next_medical_exam_date:
        # Для просроченных медосмотров
        if instance.next_medical_exam_date < current_date:
            # Проверяем, не было ли уже отправлено уведомление за последние 7 дней
            recent_notification = Notification.objects.filter(
                user=instance.user,
                notification_type='medical',
                related_entity_type='employee',
                related_entity_id=instance.id,
                created_at__gte=timezone.now() - timedelta(days=7)
            ).exists()

            if not recent_notification:
                # Сообщение для уведомления
                message = 'Ваш медицинский осмотр просрочен. Пожалуйста, обратитесь в медицинский отдел для согласования даты.'

                # Создаем уведомление для сотрудника
                Notification.objects.create(
                    user=instance.user,
                    title='Медицинский осмотр просрочен',
                    message=message,
                    notification_type='medical',
                    related_entity_type='employee',
                    related_entity_id=instance.id,
                    is_read=False
                )

                send_email_notification(
                    instance.user,
                    'Важно: Просроченный медицинский осмотр',
                    message
                )

                # Уведомляем медицинских работников
                email_subject = f'Просроченный медосмотр: {instance.user.last_name} {instance.user.first_name}'
                email_message = f'У сотрудника {instance.user.last_name} {instance.user.first_name} просрочен медицинский осмотр.'

                notify_medical_workers(
                    'Просроченный медосмотр сотрудника',
                    email_message,
                    'medical_overdue',
                    'employee',
                    instance.id,
                    email_subject,
                    email_message
                )

        # Для приближающихся медосмотров (5 дней и меньше)
        elif instance.next_medical_exam_date <= warning_date:
            # Проверяем, не было ли уже отправлено уведомление за последние 3 дня
            recent_notification = Notification.objects.filter(
                user=instance.user,
                notification_type='medical_warning',
                related_entity_type='employee',
                related_entity_id=instance.id,
                created_at__gte=timezone.now() - timedelta(days=3)
            ).exists()

            if not recent_notification:
                days_left = (instance.next_medical_exam_date - current_date).days

                # Создаем уведомление для сотрудника
                Notification.objects.create(
                    user=instance.user,
                    title='Приближается медицинский осмотр',
                    message=f'Ваш медицинский осмотр назначен через {days_left} дней. Пожалуйста, не забудьте посетить медицинский отдел.',
                    notification_type='medical_warning',
                    related_entity_type='employee',
                    related_entity_id=instance.id,
                    is_read=False
                )

                # Уведомляем медицинских работников
                notify_medical_workers(
                    'Приближающийся медосмотр сотрудника',
                    f'У сотрудника {instance.user.last_name} {instance.user.first_name} медицинский осмотр через {days_left} дней.',
                    'medical_upcoming',
                    'employee',
                    instance.id
                )


@receiver(post_save, sender=MedicalExamination)
def update_employee_on_medical_exam(sender, instance, created, **kwargs):
    """
    Сигнал, обновляющий даты медицинских осмотров сотрудника
    при создании или изменении записи о медосмотре.
    """
    if instance.employee:
        # Обновляем даты медосмотра у сотрудника
        employee = instance.employee

        # Обновляем только если даты в медосмотре новее существующих или отсутствуют
        update_needed = False

        if not employee.medical_exam_date or (instance.exam_date and instance.exam_date >= employee.medical_exam_date):
            employee.medical_exam_date = instance.exam_date
            update_needed = True

        if not employee.next_medical_exam_date or (
                instance.next_exam_date and instance.next_exam_date != employee.next_medical_exam_date):
            employee.next_medical_exam_date = instance.next_exam_date
            update_needed = True

        if update_needed:
            # Отключаем сигналы при сохранении, чтобы избежать рекурсии
            post_save.disconnect(check_medical_exam_date, sender=Employee)
            employee.save()
            post_save.connect(check_medical_exam_date, sender=Employee)

            # Если медосмотр создан медицинским работником, отправляем уведомление сотруднику
            if created:
                Notification.objects.create(
                    user=employee.user,
                    title='Назначен медицинский осмотр',
                    message=f'Вам назначен медицинский осмотр на {instance.next_exam_date.strftime("%d.%m.%Y")}.',
                    notification_type='medical_scheduled',
                    related_entity_type='medical_examination',
                    related_entity_id=instance.id,
                    is_read=False
                )


def notify_medical_workers(title, message, notification_type, entity_type=None, entity_id=None, email_subject=None,
                           email_message=None):
    """
    Вспомогательная функция для отправки уведомлений медицинским работникам.
    """
    # Получаем всех медицинских работников
    medical_workers = Employee.objects.filter(role='medical_worker')

    for worker in medical_workers:
        # Создаем уведомление в системе
        Notification.objects.create(
            user=worker.user,
            title=title,
            message=message,
            notification_type=notification_type,
            related_entity_type=entity_type,
            related_entity_id=entity_id,
            is_read=False
        )

        # Отправляем email, если указаны тема и текст письма
        if email_subject and email_message:
            send_email_notification(
                worker.user,
                email_subject,
                email_message
            )


@receiver(post_save, sender=User)
def create_employee_if_missing(sender, instance, created, **kwargs):
    """
    Создает запись Employee для новых пользователей, если её ещё нет.
    """
    if created:
        try:
            # Проверяем, существует ли уже связанный Employee
            instance.employee
        except Employee.DoesNotExist:
            # Если нет, создаем новый
            Employee.objects.create(
                user=instance,
                hire_date=timezone.now().date()
            )


@receiver(post_save, sender=Employee)
def notify_safety_specialists_on_new_employee(sender, instance, created, **kwargs):
    """
    Сигнал для уведомления специалистов по охране труда о новом сотруднике
    """
    if created:  # Только для новых сотрудников, не для обновлений
        # Получаем название отдела или 'Без подразделения' если не указан
        department_name = instance.department.name if instance.department else 'Без подразделения'

        # Получаем всех пользователей с ролью safety_specialist
        safety_specialists = Employee.objects.filter(role='safety_specialist')

        for specialist in safety_specialists:
            # Создаем уведомление для каждого специалиста по охране труда
            Notification.objects.create(
                user=specialist.user,
                title='Новый сотрудник в системе',
                message=f'В системе зарегистрирован новый сотрудник: {instance.user.last_name} {instance.user.first_name} в отделе {department_name}.',
                notification_type='new_employee',
                related_entity_type='employee',
                related_entity_id=instance.id,
                is_read=False
            )

            send_email_notification(
                specialist.user,
                'Новый сотрудник в системе',
                f'В системе зарегистрирован новый сотрудник: {instance.user.last_name} {instance.user.first_name} в отделе {department_name}.'
            )

def send_email_notification(user, subject, message):
    """
    Отправляет email-уведомление пользователю, если у него указан email.

    Args:
        user: Пользователь, которому отправляется email
        subject: Тема письма
        message: Текст письма
    """
    if user.email:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True  # Не вызывать исключение при ошибке отправки
            )
            return True
        except Exception as e:
            print(f"Error sending email to {user.email}: {str(e)}")
            return False
    return False