from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from import_export.admin import ImportExportModelAdmin, ImportExportActionModelAdmin
from import_export.formats import base_formats

from .models import (
    Department, Employee, PPEItem, PPERequest, PPEIssuance,
    Document, InstructionType, Instruction, InstructionParticipant,
    Equipment, EquipmentMaintenance, Hazard, Risk, RiskMitigationMeasure,
    Inspection, InspectionFinding, Incident, IncidentVictim, SafetyTask,
    WorkplaceAssessment, MedicalExamination, Notification, UserLog
)
from .resources import (
    UserResource, DepartmentResource, EmployeeResource, PPEItemResource,
    PPERequestResource, DocumentResource, InstructionTypeResource,
    InstructionResource, EquipmentResource, HazardResource, RiskResource,
    InspectionResource, IncidentResource, MedicalExaminationResource, UserLogResource, EquipmentMaintenanceResource, WorkplaceAssessmentResource,
    SafetyTaskResource, NotificationResource
)

try:
    AVAILABLE_FORMATS = [base_formats.CSV, base_formats.XLS, base_formats.XLSX, base_formats.JSON]
except:
    AVAILABLE_FORMATS = [base_formats.CSV, base_formats.JSON]


# Настройка админки для пользователей
class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False
    verbose_name_plural = 'Информация о сотруднике'
    fields = ('department', 'position', 'role', 'hire_date', 'medical_exam_date', 'next_medical_exam_date')


class CustomUserAdmin(UserAdmin, ImportExportModelAdmin):
    resource_class = UserResource
    inlines = (EmployeeInline,)
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'get_department', 'is_active')
    list_filter = ('employee__role', 'employee__department', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'employee__position')

    def get_role(self, obj):
        try:
            return obj.employee.get_role_display()
        except Employee.DoesNotExist:
            return '-'

    get_role.short_description = 'Роль'

    def get_department(self, obj):
        try:
            return obj.employee.department.name if obj.employee.department else '-'
        except Employee.DoesNotExist:
            return '-'

    get_department.short_description = 'Подразделение'


# Перерегистрируем модель User с нашим CustomUserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# Админка для подразделений
@admin.register(Department)
class DepartmentAdmin(ImportExportModelAdmin):
    resource_class = DepartmentResource
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    list_display = ('name', 'parent', 'get_employees_count')
    search_fields = ('name', 'description')
    list_filter = ('parent',)

    def get_employees_count(self, obj):
        return obj.employees.count()

    get_employees_count.short_description = 'Количество сотрудников'


# Админка для сотрудников
@admin.register(Employee)
class EmployeeAdmin(ImportExportModelAdmin):
    resource_class = EmployeeResource
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    list_display = ('__str__', 'position', 'department', 'role', 'hire_date', 'next_medical_exam_status')
    list_filter = ('role', 'department', 'hire_date')
    search_fields = ('user__first_name', 'user__last_name', 'position', 'personal_id_number')
    date_hierarchy = 'hire_date'

    def next_medical_exam_status(self, obj):
        if not obj.next_medical_exam_date:
            return format_html('<span style="color: gray;">Не указано</span>')

        from django.utils import timezone
        if obj.next_medical_exam_date < timezone.now().date():
            return format_html('<span style="color: red; font-weight: bold;">Просрочен ({})</span>',
                               obj.next_medical_exam_date.strftime('%d.%m.%Y'))
        else:
            return format_html('<span style="color: green;">{}</span>',
                               obj.next_medical_exam_date.strftime('%d.%m.%Y'))

    next_medical_exam_status.short_description = 'Следующий медосмотр'


# Админка для СИЗ
@admin.register(PPEItem)
class PPEItemAdmin(ImportExportModelAdmin):
    resource_class = PPEItemResource
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    list_display = ('name', 'category', 'standard_issue_period', 'manufacturer')
    list_filter = ('category',)
    search_fields = ('name', 'category', 'description', 'manufacturer', 'supplier')


# Админка для заявок на СИЗ
class PPEIssuanceInline(admin.TabularInline):
    model = PPEIssuance
    extra = 0
    fields = ('issue_date', 'quantity', 'issued_by', 'expected_return_date', 'actual_return_date')


@admin.register(PPERequest)
class PPERequestAdmin(ImportExportModelAdmin):
    resource_class = PPERequestResource
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    list_display = ('id', 'employee', 'ppe_item', 'quantity', 'request_date', 'status')
    list_filter = ('status', 'request_date', 'ppe_item__category')
    search_fields = ('employee__user__last_name', 'employee__user__first_name', 'ppe_item__name')
    date_hierarchy = 'request_date'
    inlines = [PPEIssuanceInline]


# Админка для документов
@admin.register(Document)
class DocumentAdmin(ImportExportModelAdmin):
    resource_class = DocumentResource
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    list_display = ('title', 'document_type', 'publish_date', 'effective_date', 'expiry_date', 'is_active')
    list_filter = ('document_type', 'is_active', 'publish_date')
    search_fields = ('title', 'description', 'author')
    date_hierarchy = 'publish_date'


# Админка для типов инструктажей
@admin.register(InstructionType)
class InstructionTypeAdmin(ImportExportModelAdmin):
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    resource_class = InstructionTypeResource
    list_display = ('name', 'period_days')
    search_fields = ('name', 'description')


# Админка для инструктажей
class InstructionParticipantInline(admin.TabularInline):
    model = InstructionParticipant
    extra = 0
    fields = ('employee', 'status', 'test_result')


@admin.register(Instruction)
class InstructionAdmin(ImportExportModelAdmin):
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    resource_class = InstructionResource
    list_display = ('instruction_date', 'instruction_type', 'department', 'instructor', 'get_participants_count',
                    'next_instruction_date')
    list_filter = ('instruction_type', 'instruction_date', 'department')
    search_fields = ('instructor__last_name', 'instructor__first_name', 'location')
    date_hierarchy = 'instruction_date'
    inlines = [InstructionParticipantInline]

    def get_participants_count(self, obj):
        return obj.participants.count()

    get_participants_count.short_description = 'Количество участников'


# Админка для оборудования
@admin.register(Equipment)
class EquipmentAdmin(ImportExportModelAdmin):
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    resource_class = EquipmentResource
    list_display = (
    'name', 'model', 'serial_number', 'equipment_type', 'department', 'status', 'next_maintenance_status')
    list_filter = ('status', 'equipment_type', 'department')
    search_fields = ('name', 'model', 'serial_number', 'manufacturer')

    def next_maintenance_status(self, obj):
        if not obj.next_maintenance_date:
            return format_html('<span style="color: gray;">Не указано</span>')

        from django.utils import timezone
        if obj.next_maintenance_date < timezone.now():
            return format_html('<span style="color: red; font-weight: bold;">Просрочено ({})</span>',
                               obj.next_maintenance_date.strftime('%d.%m.%Y %H:%M'))
        else:
            return format_html('<span style="color: green;">{}</span>',
                               obj.next_maintenance_date.strftime('%d.%m.%Y %H:%M'))

    next_maintenance_status.short_description = 'Следующее ТО'


# Админка для обслуживания оборудования
@admin.register(EquipmentMaintenance)
class EquipmentMaintenanceAdmin(ImportExportModelAdmin):  # Изменено с ImportExportActionModelAdmin
    resource_class = EquipmentMaintenanceResource
    import_formats = AVAILABLE_FORMATS
    export_formats = AVAILABLE_FORMATS
    list_display = ('equipment', 'maintenance_type', 'maintenance_date', 'performed_by', 'result')
    list_filter = ('maintenance_type', 'maintenance_date', 'equipment__equipment_type')
    search_fields = ('equipment__name', 'description', 'performed_by__last_name')
    date_hierarchy = 'maintenance_date'


# Админка для опасностей
@admin.register(Hazard)
class HazardAdmin(ImportExportModelAdmin):
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    resource_class = HazardResource
    list_display = ('name', 'category', 'get_risks_count')
    list_filter = ('category',)
    search_fields = ('name', 'description', 'category')

    def get_risks_count(self, obj):
        return obj.risks.count()

    get_risks_count.short_description = 'Количество рисков'


# Админка для рисков
class RiskMitigationMeasureInline(admin.TabularInline):
    model = RiskMitigationMeasure
    extra = 0
    fields = ('description', 'status', 'responsible_person', 'deadline', 'effectiveness_rating')


@admin.register(Risk)
class RiskAdmin(ImportExportModelAdmin):
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    resource_class = RiskResource
    list_display = (
    'hazard', 'department', 'location', 'level', 'probability', 'severity', 'risk_score', 'evaluation_date')
    list_filter = ('level', 'hazard__category', 'department')
    search_fields = ('hazard__name', 'location', 'description')
    date_hierarchy = 'evaluation_date'
    inlines = [RiskMitigationMeasureInline]

    def risk_score(self, obj):
        score = obj.probability * obj.severity
        color = 'green'
        if score > 6:
            color = 'red'
        elif score > 3:
            color = 'orange'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, score)

    risk_score.short_description = 'Оценка риска'


# Админка для проверок
class InspectionFindingInline(admin.TabularInline):
    model = InspectionFinding
    extra = 0
    fields = ('description', 'severity', 'location', 'responsible_department', 'deadline', 'status')


@admin.register(Inspection)
class InspectionAdmin(ImportExportModelAdmin):
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    resource_class = InspectionResource
    list_display = ('title', 'inspection_type', 'department', 'start_date', 'end_date', 'status', 'get_findings_count')
    list_filter = ('status', 'inspection_type', 'department')
    search_fields = ('title', 'description', 'lead_inspector__last_name')
    date_hierarchy = 'start_date'
    inlines = [InspectionFindingInline]

    def get_findings_count(self, obj):
        return obj.findings.count()

    get_findings_count.short_description = 'Количество нарушений'


# Админка для происшествий
class IncidentVictimInline(admin.TabularInline):
    model = IncidentVictim
    extra = 0
    fields = ('employee', 'injury_description', 'medical_assistance', 'work_days_lost')


@admin.register(Incident)
class IncidentAdmin(ImportExportModelAdmin):
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    resource_class = IncidentResource
    list_display = (
    'title', 'incident_type', 'location', 'department', 'incident_date', 'severity', 'investigation_status')
    list_filter = ('incident_type', 'severity', 'investigation_status', 'department')
    search_fields = ('title', 'description', 'location')
    date_hierarchy = 'incident_date'
    inlines = [IncidentVictimInline]


# Админка для медицинских осмотров
@admin.register(MedicalExamination)
class MedicalExaminationAdmin(ImportExportModelAdmin):
    import_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    export_formats = [base_formats.CSV, base_formats.XLS, base_formats.XLSX]
    resource_class = MedicalExaminationResource
    list_display = ('employee', 'exam_date', 'exam_type', 'result', 'medical_facility', 'next_exam_date')
    list_filter = ('exam_type', 'exam_date', 'result')
    search_fields = ('employee__user__last_name', 'employee__user__first_name', 'medical_facility')
    date_hierarchy = 'exam_date'


# Админка для специальной оценки условий труда
@admin.register(WorkplaceAssessment)
class WorkplaceAssessmentAdmin(ImportExportModelAdmin):  # Изменено с ImportExportActionModelAdmin
    resource_class = WorkplaceAssessmentResource
    import_formats = AVAILABLE_FORMATS
    export_formats = AVAILABLE_FORMATS
    list_display = ('workplace_name', 'department', 'assessment_date', 'next_assessment_date', 'result', 'hazard_class')
    list_filter = ('hazard_class', 'result', 'department')
    search_fields = ('workplace_name', 'assessor', 'notes')
    date_hierarchy = 'assessment_date'


# Админка для задач по охране труда
@admin.register(SafetyTask)
class SafetyTaskAdmin(ImportExportModelAdmin):  # Изменено с ImportExportActionModelAdmin
    resource_class = SafetyTaskResource
    import_formats = AVAILABLE_FORMATS
    export_formats = AVAILABLE_FORMATS
    list_display = ('title', 'task_type', 'priority', 'status', 'assigned_to', 'department', 'deadline')
    list_filter = ('status', 'priority', 'task_type', 'department')
    search_fields = ('title', 'description', 'assigned_to__last_name')
    date_hierarchy = 'deadline'


# Админка для уведомлений
@admin.register(Notification)
class NotificationAdmin(ImportExportModelAdmin):  # Изменено с ImportExportActionModelAdmin
    resource_class = NotificationResource
    import_formats = AVAILABLE_FORMATS
    export_formats = AVAILABLE_FORMATS
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'user__last_name', 'title', 'message')
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Отметить как прочитанные"

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Отметить как непрочитанные"


# Админка для логов пользователей
@admin.register(UserLog)
class UserLogAdmin(ImportExportActionModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__username', 'user__last_name', 'action', 'ip_address')
    date_hierarchy = 'timestamp'
    readonly_fields = ('user', 'action', 'ip_address', 'user_agent', 'details', 'timestamp')


# Настройка заголовка и названия админки
admin.site.site_header = 'Орион - Система безопасности на рабочем месте'
admin.site.site_title = 'Орион'
admin.site.index_title = 'Панель администратора'