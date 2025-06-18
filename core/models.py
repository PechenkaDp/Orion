from django.db.models import JSONField
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, datetime
import time

# Перечисления для статусов
TASK_STATUS_CHOICES = [
    ('new', 'Новая'),
    ('in_progress', 'В обработке'),
    ('completed', 'Выполнено'),
    ('canceled', 'Отменено'),
]

RISK_LEVEL_CHOICES = [
    ('low', 'Низкий'),
    ('medium', 'Средний'),
    ('high', 'Высокий'),
    ('critical', 'Критический'),
]

EQUIPMENT_STATUS_CHOICES = [
    ('operational', 'Исправно'),
    ('requires_maintenance', 'Требуется обслуживание'),
    ('under_maintenance', 'На обслуживании'),
    ('decommissioned', 'Выведено из эксплуатации'),
]


# Подразделения
class Department(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children',
                               verbose_name='Родительское подразделение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'
        ordering = ['name']

    def __str__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee', verbose_name='Пользователь')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='employees', verbose_name='Подразделение')
    position = models.CharField(max_length=255, verbose_name='Должность')
    role = models.CharField(max_length=50, choices=[
        ('admin', 'Администратор'),
        ('safety_specialist', 'Специалист по охране труда'),
        ('department_head', 'Руководитель подразделения'),
        ('employee', 'Сотрудник'),
        ('medical_worker', 'Медицинский работник'),
        ('technician', 'Техник')
    ], default='employee', verbose_name='Роль')
    hire_date = models.DateField(verbose_name='Дата приема на работу')
    medical_exam_date = models.DateField(null=True, blank=True, verbose_name='Дата последнего медосмотра')
    next_medical_exam_date = models.DateField(null=True, blank=True, verbose_name='Дата следующего медосмотра')
    personal_id_number = models.CharField(max_length=50, unique=True, null=True, blank=True,
                                          verbose_name='Табельный номер')
    emergency_contact = models.CharField(max_length=255, null=True, blank=True, verbose_name='Экстренный контакт')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')


    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name}"

    @property
    def full_name(self):
        return f"{self.user.last_name} {self.user.first_name}"


class PPEItem(models.Model):
    name = models.CharField(max_length=255, verbose_name='Наименование')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    category = models.CharField(max_length=100, verbose_name='Категория')
    standard_issue_period = models.IntegerField(null=True, blank=True, verbose_name='Стандартный период выдачи (дни)')
    certification_number = models.CharField(max_length=100, null=True, blank=True, verbose_name='Номер сертификата')
    manufacturer = models.CharField(max_length=255, null=True, blank=True, verbose_name='Производитель')
    supplier = models.CharField(max_length=255, null=True, blank=True, verbose_name='Поставщик')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'СИЗ'
        verbose_name_plural = 'СИЗ'
        ordering = ['name']

    def __str__(self):
        return self.name


class PPERequest(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='ppe_requests',
                                 verbose_name='Сотрудник')
    ppe_item = models.ForeignKey(PPEItem, on_delete=models.CASCADE, related_name='requests', verbose_name='СИЗ')
    quantity = models.IntegerField(default=1, verbose_name='Количество')
    request_date = models.DateTimeField(default=timezone.now, verbose_name='Дата заявки')
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='new', verbose_name='Статус')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='processed_ppe_requests', verbose_name='Обработал')
    processed_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата обработки')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Заявка на СИЗ'
        verbose_name_plural = 'Заявки на СИЗ'
        ordering = ['-request_date']

    def __str__(self):
        return f"Заявка #{self.pk} от {self.employee} на {self.ppe_item.name}"


class PPEIssuance(models.Model):
    request = models.ForeignKey(PPERequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='issuances',
                                verbose_name='Заявка')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='ppe_issuances',
                                 verbose_name='Сотрудник')
    ppe_item = models.ForeignKey(PPEItem, on_delete=models.CASCADE, related_name='issuances', verbose_name='СИЗ')
    quantity = models.IntegerField(default=1, verbose_name='Количество')
    issue_date = models.DateTimeField(default=timezone.now, verbose_name='Дата выдачи')
    expected_return_date = models.DateTimeField(null=True, blank=True, verbose_name='Ожидаемая дата возврата')
    actual_return_date = models.DateTimeField(null=True, blank=True, verbose_name='Фактическая дата возврата')
    issued_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='issued_ppe', verbose_name='Выдал')
    condition_on_issue = models.TextField(blank=True, null=True, verbose_name='Состояние при выдаче')
    condition_on_return = models.TextField(blank=True, null=True, verbose_name='Состояние при возврате')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Выдача СИЗ'
        verbose_name_plural = 'Выдачи СИЗ'
        ordering = ['-issue_date']

    def __str__(self):
        return f"Выдача {self.ppe_item.name} для {self.employee} от {self.issue_date.strftime('%d.%m.%Y')}"


class Document(models.Model):
    title = models.CharField(max_length=255, verbose_name='Название')
    document_type = models.CharField(max_length=100, verbose_name='Тип документа')
    file = models.FileField(upload_to='documents/', blank=True, null=True, verbose_name='Файл')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    publish_date = models.DateField(null=True, blank=True, verbose_name='Дата публикации')
    effective_date = models.DateField(null=True, blank=True, verbose_name='Дата вступления в силу')
    expiry_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания срока действия')
    version = models.CharField(max_length=50, null=True, blank=True, verbose_name='Версия')
    author = models.CharField(max_length=255, null=True, blank=True, verbose_name='Автор')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title


class InstructionType(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    period_days = models.IntegerField(null=True, blank=True, verbose_name='Периодичность (дни)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Тип инструктажа'
        verbose_name_plural = 'Типы инструктажей'
        ordering = ['name']

    def __str__(self):
        return self.name


class Instruction(models.Model):
    instruction_type = models.ForeignKey(InstructionType, on_delete=models.CASCADE, related_name='instructions',
                                         verbose_name='Тип инструктажа')
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conducted_instructions',
                                   verbose_name='Инструктор')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='instructions', verbose_name='Подразделение')
    instruction_date = models.DateTimeField(default=timezone.now, verbose_name='Дата проведения')
    next_instruction_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата следующего инструктажа')
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name='Место проведения')
    duration = models.IntegerField(null=True, blank=True, verbose_name='Продолжительность (минуты)')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Инструктаж'
        verbose_name_plural = 'Инструктажи'
        ordering = ['-instruction_date']

    def __str__(self):
        return f"{self.instruction_type.name} от {self.instruction_date.strftime('%d.%m.%Y')}"


class InstructionParticipant(models.Model):
    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE, related_name='participants',
                                    verbose_name='Инструктаж')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='instruction_participations',
                                 verbose_name='Сотрудник')
    status = models.CharField(max_length=50, default='attended', verbose_name='Статус')
    test_result = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                      verbose_name='Результат проверки знаний')
    signature_path = models.CharField(max_length=255, null=True, blank=True, verbose_name='Путь к файлу с подписью')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Участник инструктажа'
        verbose_name_plural = 'Участники инструктажей'
        unique_together = ('instruction', 'employee')

    def __str__(self):
        return f"{self.employee} - {self.instruction}"


class Equipment(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    equipment_type = models.CharField(max_length=100, verbose_name='Тип оборудования')
    model = models.CharField(max_length=255, blank=True, null=True, verbose_name='Модель')
    serial_number = models.CharField(max_length=255, unique=True, blank=True, null=True, verbose_name='Серийный номер')
    manufacturer = models.CharField(max_length=255, blank=True, null=True, verbose_name='Производитель')
    purchase_date = models.DateField(null=True, blank=True, verbose_name='Дата приобретения')
    warranty_expiry_date = models.DateField(null=True, blank=True, verbose_name='Дата окончания гарантии')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='equipment', verbose_name='Подразделение')
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name='Местоположение')
    status = models.CharField(max_length=20, choices=EQUIPMENT_STATUS_CHOICES, default='operational',
                              verbose_name='Статус')
    last_maintenance_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата последнего обслуживания')
    next_maintenance_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата следующего обслуживания')
    responsible_person = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='responsible_for_equipment', verbose_name='Ответственное лицо')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Оборудование'
        verbose_name_plural = 'Оборудование'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.model or 'без модели'})"


class EquipmentMaintenance(models.Model):
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenance_records',
                                  verbose_name='Оборудование')
    maintenance_type = models.CharField(max_length=100, verbose_name='Тип обслуживания')
    maintenance_date = models.DateTimeField(default=timezone.now, verbose_name='Дата обслуживания')
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='performed_maintenance', verbose_name='Выполнил')
    description = models.TextField(blank=True, null=True, verbose_name='Описание работ')
    result = models.CharField(max_length=100, verbose_name='Результат')
    next_maintenance_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата следующего обслуживания')
    documents_path = models.CharField(max_length=255, blank=True, null=True, verbose_name='Путь к документам')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Обслуживание оборудования'
        verbose_name_plural = 'Обслуживание оборудования'
        ordering = ['-maintenance_date']

    def __str__(self):
        return f"Обслуживание {self.equipment.name} от {self.maintenance_date.strftime('%d.%m.%Y')}"


class Hazard(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    category = models.CharField(max_length=100, verbose_name='Категория')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Опасность'
        verbose_name_plural = 'Опасности'
        ordering = ['name']

    def __str__(self):
        return self.name


class Risk(models.Model):
    hazard = models.ForeignKey(Hazard, on_delete=models.CASCADE, related_name='risks', verbose_name='Опасность')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='risks',
                                   verbose_name='Подразделение')
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name='Местоположение')
    level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, verbose_name='Уровень риска')
    probability = models.DecimalField(max_digits=3, decimal_places=2, verbose_name='Вероятность (0-1)')
    severity = models.IntegerField(verbose_name='Тяжесть последствий (1-10)')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    evaluation_date = models.DateTimeField(default=timezone.now, verbose_name='Дата оценки')
    evaluated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='evaluated_risks', verbose_name='Оценил')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Риск'
        verbose_name_plural = 'Риски'
        ordering = ['-evaluation_date']

    def __str__(self):
        return f"{self.hazard.name} - {self.get_level_display()}"

    @property
    def risk_score(self):
        return round(self.probability * self.severity, 1)


class RiskMitigationMeasure(models.Model):
    risk = models.ForeignKey(Risk, on_delete=models.CASCADE, related_name='mitigation_measures', verbose_name='Риск')
    description = models.TextField(verbose_name='Описание мероприятия')
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='new', verbose_name='Статус')
    responsible_person = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='risk_mitigation_tasks', verbose_name='Ответственный')
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='Срок выполнения')
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата выполнения')
    effectiveness_rating = models.IntegerField(null=True, blank=True, verbose_name='Оценка эффективности (1-10)')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Мероприятие по снижению риска'
        verbose_name_plural = 'Мероприятия по снижению рисков'
        ordering = ['-created_at']

    def __str__(self):
        return f"Мероприятие для {self.risk.hazard.name}"


class Inspection(models.Model):
    title = models.CharField(max_length=255, verbose_name='Название')
    inspection_type = models.CharField(max_length=100, verbose_name='Тип проверки')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='inspections', verbose_name='Подразделение')
    start_date = models.DateTimeField(verbose_name='Дата начала')
    end_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата окончания')
    lead_inspector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='led_inspections', verbose_name='Главный проверяющий')
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='new', verbose_name='Статус')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    result = models.TextField(blank=True, null=True, verbose_name='Результат')
    report_path = models.CharField(max_length=255, blank=True, null=True, verbose_name='Путь к отчету')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Проверка'
        verbose_name_plural = 'Проверки'
        ordering = ['-start_date']

    def __str__(self):
        return self.title


class InspectionFinding(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name='findings',
                                   verbose_name='Проверка')
    description = models.TextField(verbose_name='Описание нарушения')
    severity = models.CharField(max_length=50, verbose_name='Тяжесть')
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name='Местоположение')
    responsible_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                               related_name='responsible_for_findings',
                                               verbose_name='Ответственное подразделение')
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='Срок устранения')
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='new', verbose_name='Статус')
    resolution = models.TextField(blank=True, null=True, verbose_name='Решение')
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата устранения')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='verified_findings', verbose_name='Проверил')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Нарушение'
        verbose_name_plural = 'Нарушения'
        ordering = ['-created_at']

    def __str__(self):
        return f"Нарушение в рамках {self.inspection.title}"


class Incident(models.Model):
    title = models.CharField(max_length=255, verbose_name='Название')
    incident_type = models.CharField(max_length=100, verbose_name='Тип происшествия')
    location = models.CharField(max_length=255, verbose_name='Место происшествия')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='incidents', verbose_name='Подразделение')
    incident_date = models.DateTimeField(verbose_name='Дата происшествия')
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='reported_incidents', verbose_name='Сообщил')
    report_date = models.DateTimeField(default=timezone.now, verbose_name='Дата сообщения')
    description = models.TextField(verbose_name='Описание')
    severity = models.CharField(max_length=50, verbose_name='Тяжесть')
    immediate_actions = models.TextField(blank=True, null=True, verbose_name='Первоначальные действия')
    investigation_status = models.CharField(max_length=50, default='pending', verbose_name='Статус расследования')
    root_cause = models.TextField(blank=True, null=True, verbose_name='Корневая причина')
    preventive_measures = models.TextField(blank=True, null=True, verbose_name='Превентивные меры')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Происшествие'
        verbose_name_plural = 'Происшествия'
        ordering = ['-incident_date']

    def __str__(self):
        return self.title


class IncidentVictim(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='victims',
                                 verbose_name='Происшествие')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='incident_involvements',
                                 verbose_name='Сотрудник')
    injury_description = models.TextField(blank=True, null=True, verbose_name='Описание травмы')
    medical_assistance = models.CharField(max_length=255, blank=True, null=True, verbose_name='Медицинская помощь')
    work_days_lost = models.IntegerField(default=0, verbose_name='Потерянные рабочие дни')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Пострадавший'
        verbose_name_plural = 'Пострадавшие'

    def __str__(self):
        return f"{self.employee} в {self.incident.title}"


class SafetyTask(models.Model):
    title = models.CharField(max_length=255, verbose_name='Название')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    task_type = models.CharField(max_length=100, verbose_name='Тип задачи')
    priority = models.CharField(max_length=50, default='medium', verbose_name='Приоритет')
    status = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='new', verbose_name='Статус')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='assigned_safety_tasks', verbose_name='Назначено')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='created_safety_tasks', verbose_name='Назначил')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='safety_tasks', verbose_name='Подразделение')
    start_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата начала')
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='Срок выполнения')
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата выполнения')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Задача по охране труда'
        verbose_name_plural = 'Задачи по охране труда'
        ordering = ['-created_at']

    def __str__(self):
        return self.title



class WorkplaceAssessment(models.Model):
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='workplace_assessments', verbose_name='Подразделение')
    workplace_name = models.CharField(max_length=255, verbose_name='Название рабочего места')
    assessment_date = models.DateField(verbose_name='Дата оценки')
    next_assessment_date = models.DateField(verbose_name='Дата следующей оценки')
    assessor = models.CharField(max_length=255, verbose_name='Оценщик')
    result = models.CharField(max_length=50, verbose_name='Результат')
    hazard_class = models.IntegerField(verbose_name='Класс вредности (1-4)')
    report_number = models.CharField(max_length=100, verbose_name='Номер отчета')
    report_file = models.FileField(upload_to='souf_reports/', blank=True, null=True, verbose_name='Файл отчета')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'СОУТ'
        verbose_name_plural = 'СОУТ'
        ordering = ['-assessment_date']

    def __str__(self):
        return f"СОУТ: {self.workplace_name} от {self.assessment_date.strftime('%d.%m.%Y')}"


class MedicalExamination(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='medical_exams',
                                 verbose_name='Сотрудник')
    exam_date = models.DateField(verbose_name='Дата осмотра')
    next_exam_date = models.DateField(verbose_name='Дата следующего осмотра')
    exam_type = models.CharField(max_length=100, verbose_name='Тип осмотра')
    medical_facility = models.CharField(max_length=255, verbose_name='Медицинское учреждение')
    doctor = models.CharField(max_length=255, blank=True, null=True, verbose_name='Врач')
    result = models.CharField(max_length=50, verbose_name='Результат')
    recommendations = models.TextField(blank=True, null=True, verbose_name='Рекомендации')
    restrictions = models.TextField(blank=True, null=True, verbose_name='Ограничения')
    document = models.FileField(upload_to='medical_docs/', blank=True, null=True, verbose_name='Документ')
    notes = models.TextField(blank=True, null=True, verbose_name='Примечания')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Медицинский осмотр'
        verbose_name_plural = 'Медицинские осмотры'
        ordering = ['-exam_date']

    def __str__(self):
        return f"Медосмотр {self.employee} от {self.exam_date.strftime('%d.%m.%Y')}"


class UserLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    details = JSONField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Лог пользователя'
        verbose_name_plural = 'Логи пользователей'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.timestamp}"

def instruction_material_file_path(instance, filename):
    ext = filename.split('.')[-1]
    safe_title = ''.join(c for c in instance.title if c.isalnum() or c in (' ', '.', '-', '_')).strip()
    safe_title = safe_title.replace(' ', '_')
    timestamp = int(time.time())
    return f'instruction_materials/{safe_title}_{timestamp}.{ext}'

class InstructionMaterial(models.Model):
    """Materials associated with an instruction for study"""
    instruction = models.ForeignKey(Instruction, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=255, verbose_name='Название')
    content = models.TextField(verbose_name='Содержание')
    file = models.FileField(upload_to=instruction_material_file_path, blank=True, null=True, verbose_name='Файл')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок отображения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Материал инструктажа'
        verbose_name_plural = 'Материалы инструктажей'
        ordering = ['instruction', 'order']

    def __str__(self):
        return f"{self.instruction} - {self.title}"


class InstructionTest(models.Model):
    """Test associated with an instruction"""
    instruction = models.OneToOneField(Instruction, on_delete=models.CASCADE, related_name='test')
    title = models.CharField(max_length=255, verbose_name='Название теста')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    passing_score = models.PositiveIntegerField(default=70, verbose_name='Проходной балл (%)')
    time_limit = models.PositiveIntegerField(default=30, verbose_name='Ограничение времени (мин)',
                                             help_text='0 - без ограничения')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Тест к инструктажу'
        verbose_name_plural = 'Тесты к инструктажам'

    def __str__(self):
        return f"Тест: {self.title}"


class TestQuestion(models.Model):
    """Question for an instruction test"""
    test = models.ForeignKey(InstructionTest, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField(verbose_name='Текст вопроса')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок отображения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Вопрос теста'
        verbose_name_plural = 'Вопросы тестов'
        ordering = ['test', 'order']

    def __str__(self):
        return f"Вопрос {self.order}: {self.question_text[:50]}..."


class TestAnswer(models.Model):
    """Answer for a test question"""
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=255, verbose_name='Текст ответа')
    is_correct = models.BooleanField(default=False, verbose_name='Правильный ответ')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок отображения')

    class Meta:
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'
        ordering = ['question', 'order']

    def __str__(self):
        return f"Ответ: {self.answer_text[:50]}"


class TestResult(models.Model):
    """Results of a test taken by an employee"""
    test = models.ForeignKey(InstructionTest, on_delete=models.CASCADE, related_name='results')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='test_results')
    start_time = models.DateTimeField(auto_now_add=True, verbose_name='Время начала')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Время окончания')
    score = models.PositiveIntegerField(default=0, verbose_name='Набранные баллы')
    max_score = models.PositiveIntegerField(default=0, verbose_name='Максимальный балл')
    score_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                        verbose_name='Процент правильных ответов')
    passed = models.BooleanField(default=False, verbose_name='Пройден')
    reviewed = models.BooleanField(default=False, verbose_name='Проверен')
    reviewer_notes = models.TextField(blank=True, null=True, verbose_name='Примечания проверяющего')

    class Meta:
        verbose_name = 'Результат теста'
        verbose_name_plural = 'Результаты тестов'
        ordering = ['-start_time']

    def __str__(self):
        return f"Тест {self.test.title} - {self.employee} - {self.score_percent}%"

    def calculate_score(self):
        """Calculate the score based on answers"""
        # This would be implemented to calculate the score based on user answers
        # We'll need to implement this in the view
        pass


class TestAnswerSubmission(models.Model):
    """User's submitted answers for a test"""
    test_result = models.ForeignKey(TestResult, on_delete=models.CASCADE, related_name='answer_submissions')
    question = models.ForeignKey(TestQuestion, on_delete=models.CASCADE, related_name='submissions')
    answer = models.ForeignKey(TestAnswer, on_delete=models.CASCADE, related_name='submissions')
    is_correct = models.BooleanField(default=False, verbose_name='Правильно')

    class Meta:
        verbose_name = 'Ответ на тест'
        verbose_name_plural = 'Ответы на тесты'

    def __str__(self):
        return f"Ответ {self.employee} на вопрос {self.question.id}"
class EvacuationNotification(models.Model):
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    message = models.TextField(verbose_name='Сообщение')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='evacuation_notifications', verbose_name='Подразделение')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_evacuation_notifications',
                                   verbose_name='Создано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_active = models.BooleanField(default=True, verbose_name='Активно')

    class Meta:
        verbose_name = 'Уведомление об эвакуации'
        verbose_name_plural = 'Уведомления об эвакуации'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='Пользователь')
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    message = models.TextField(verbose_name='Сообщение')
    notification_type = models.CharField(max_length=50, verbose_name='Тип уведомления')
    related_entity_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='Тип связанной сущности')
    related_entity_id = models.IntegerField(blank=True, null=True, verbose_name='ID связанной сущности')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} для {self.user.username}"

