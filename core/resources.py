from import_export import resources
from import_export.fields import Field
from .models import (
    Department, Employee, PPEItem, PPERequest, PPEIssuance,
    Document, InstructionType, Instruction, InstructionParticipant,
    Equipment, EquipmentMaintenance, Hazard, Risk, RiskMitigationMeasure,
    Inspection, InspectionFinding, Incident, IncidentVictim, SafetyTask,
    WorkplaceAssessment, MedicalExamination, Notification, UserLog
)
from django.contrib.auth.models import User


# Ресурс для пользователя
class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'date_joined')
        export_order = fields


# Ресурс для подразделения
class DepartmentResource(resources.ModelResource):
    parent_name = Field()

    class Meta:
        model = Department
        fields = ('id', 'name', 'description', 'parent', 'parent_name', 'created_at', 'updated_at')
        export_order = fields

    def dehydrate_parent_name(self, department):
        return department.parent.name if department.parent else ""


# Ресурс для сотрудника
class EmployeeResource(resources.ModelResource):
    department_name = Field()
    user_full_name = Field()

    class Meta:
        model = Employee
        fields = ('id', 'user__username', 'user_full_name', 'department', 'department_name',
                  'position', 'role', 'hire_date', 'medical_exam_date', 'next_medical_exam_date',
                  'personal_id_number', 'emergency_contact', 'notes')
        export_order = fields

    def dehydrate_department_name(self, employee):
        return employee.department.name if employee.department else ""

    def dehydrate_user_full_name(self, employee):
        return f"{employee.user.last_name} {employee.user.first_name}"


# Ресурс для СИЗ
class PPEItemResource(resources.ModelResource):
    class Meta:
        model = PPEItem
        fields = ('id', 'name', 'description', 'category', 'standard_issue_period',
                  'certification_number', 'manufacturer', 'supplier', 'notes')
        export_order = fields


# Ресурс для заявок на СИЗ
class PPERequestResource(resources.ModelResource):
    employee_name = Field()
    ppe_item_name = Field()
    processed_by_name = Field()

    class Meta:
        model = PPERequest
        fields = ('id', 'employee', 'employee_name', 'ppe_item', 'ppe_item_name',
                  'quantity', 'request_date', 'status', 'processed_by', 'processed_by_name',
                  'processed_date', 'notes')
        export_order = fields

    def dehydrate_employee_name(self, ppe_request):
        return str(ppe_request.employee)

    def dehydrate_ppe_item_name(self, ppe_request):
        return ppe_request.ppe_item.name

    def dehydrate_processed_by_name(self, ppe_request):
        return str(ppe_request.processed_by) if ppe_request.processed_by else ""


# Ресурс для документов
class DocumentResource(resources.ModelResource):
    class Meta:
        model = Document
        fields = ('id', 'title', 'document_type', 'description', 'publish_date',
                  'effective_date', 'expiry_date', 'version', 'author', 'is_active')
        export_order = fields


# Ресурс для типов инструктажей
class InstructionTypeResource(resources.ModelResource):
    class Meta:
        model = InstructionType
        fields = ('id', 'name', 'description', 'period_days')
        export_order = fields


# Ресурс для инструктажей
class InstructionResource(resources.ModelResource):
    instructor_name = Field()
    instruction_type_name = Field()
    department_name = Field()

    class Meta:
        model = Instruction
        fields = ('id', 'instruction_type', 'instruction_type_name', 'instructor', 'instructor_name',
                  'department', 'department_name', 'instruction_date', 'next_instruction_date',
                  'location', 'duration', 'notes')
        export_order = fields

    def dehydrate_instructor_name(self, instruction):
        return f"{instruction.instructor.last_name} {instruction.instructor.first_name}"

    def dehydrate_instruction_type_name(self, instruction):
        return instruction.instruction_type.name

    def dehydrate_department_name(self, instruction):
        return instruction.department.name if instruction.department else ""


# Ресурс для оборудования
class EquipmentResource(resources.ModelResource):
    department_name = Field()
    responsible_person_name = Field()

    class Meta:
        model = Equipment
        fields = ('id', 'name', 'equipment_type', 'model', 'serial_number', 'manufacturer',
                  'purchase_date', 'warranty_expiry_date', 'department', 'department_name',
                  'location', 'status', 'last_maintenance_date', 'next_maintenance_date',
                  'responsible_person', 'responsible_person_name', 'notes')
        export_order = fields

    def dehydrate_department_name(self, equipment):
        return equipment.department.name if equipment.department else ""

    def dehydrate_responsible_person_name(self, equipment):
        return str(equipment.responsible_person) if equipment.responsible_person else ""


# Ресурс для опасностей
class HazardResource(resources.ModelResource):
    class Meta:
        model = Hazard
        fields = ('id', 'name', 'description', 'category')
        export_order = fields


# Ресурс для рисков
class RiskResource(resources.ModelResource):
    hazard_name = Field()
    department_name = Field()
    evaluated_by_name = Field()

    class Meta:
        model = Risk
        fields = ('id', 'hazard', 'hazard_name', 'department', 'department_name', 'location',
                  'level', 'probability', 'severity', 'description', 'evaluation_date',
                  'evaluated_by', 'evaluated_by_name')
        export_order = fields

    def dehydrate_hazard_name(self, risk):
        return risk.hazard.name

    def dehydrate_department_name(self, risk):
        return risk.department.name if risk.department else ""

    def dehydrate_evaluated_by_name(self, risk):
        return f"{risk.evaluated_by.last_name} {risk.evaluated_by.first_name}" if risk.evaluated_by else ""


# Ресурс для проверок
class InspectionResource(resources.ModelResource):
    department_name = Field()
    lead_inspector_name = Field()

    class Meta:
        model = Inspection
        fields = ('id', 'title', 'inspection_type', 'department', 'department_name',
                  'start_date', 'end_date', 'lead_inspector', 'lead_inspector_name',
                  'status', 'description', 'result')
        export_order = fields

    def dehydrate_department_name(self, inspection):
        return inspection.department.name if inspection.department else ""

    def dehydrate_lead_inspector_name(self, inspection):
        return f"{inspection.lead_inspector.last_name} {inspection.lead_inspector.first_name}" if inspection.lead_inspector else ""


# Ресурс для происшествий
class IncidentResource(resources.ModelResource):
    department_name = Field()
    reported_by_name = Field()

    class Meta:
        model = Incident
        fields = ('id', 'title', 'incident_type', 'location', 'department', 'department_name',
                  'incident_date', 'reported_by', 'reported_by_name', 'report_date', 'description',
                  'severity', 'investigation_status', 'root_cause')
        export_order = fields

    def dehydrate_department_name(self, incident):
        return incident.department.name if incident.department else ""

    def dehydrate_reported_by_name(self, incident):
        return f"{incident.reported_by.last_name} {incident.reported_by.first_name}" if incident.reported_by else ""


# Ресурс для медицинских осмотров
class MedicalExaminationResource(resources.ModelResource):
    employee_name = Field()

    class Meta:
        model = MedicalExamination
        fields = ('id', 'employee', 'employee_name', 'exam_date', 'next_exam_date',
                  'exam_type', 'medical_facility', 'doctor', 'result', 'recommendations',
                  'restrictions', 'notes')
        export_order = fields

    def dehydrate_employee_name(self, exam):
        return str(exam.employee)

# Ресурс для логов пользователей
class UserLogResource(resources.ModelResource):
    user_name = Field()

    class Meta:
        model = UserLog
        fields = ('id', 'user__username', 'user_name', 'action', 'ip_address',
                 'user_agent', 'timestamp')
        export_order = fields

    def dehydrate_user_name(self, userlog):
        return f"{userlog.user.last_name} {userlog.user.first_name}" if userlog.user else ""


# Ресурс для обслуживания оборудования
class EquipmentMaintenanceResource(resources.ModelResource):
    equipment_name = Field()
    performed_by_name = Field()

    class Meta:
        model = EquipmentMaintenance
        fields = ('id', 'equipment', 'equipment_name', 'maintenance_type',
                 'maintenance_date', 'performed_by', 'performed_by_name',
                 'description', 'result', 'next_maintenance_date', 'notes')
        export_order = fields

    def dehydrate_equipment_name(self, maintenance):
        return maintenance.equipment.name if maintenance.equipment else ""

    def dehydrate_performed_by_name(self, maintenance):
        return f"{maintenance.performed_by.last_name} {maintenance.performed_by.first_name}" if maintenance.performed_by else ""


# Ресурс для СОУТ
class WorkplaceAssessmentResource(resources.ModelResource):
    department_name = Field()

    class Meta:
        model = WorkplaceAssessment
        fields = ('id', 'department', 'department_name', 'workplace_name',
                 'assessment_date', 'next_assessment_date', 'assessor',
                 'result', 'hazard_class', 'report_number', 'notes')
        export_order = fields

    def dehydrate_department_name(self, assessment):
        return assessment.department.name if assessment.department else ""


# Ресурс для задач по охране труда
class SafetyTaskResource(resources.ModelResource):
    assigned_to_name = Field()
    assigned_by_name = Field()
    department_name = Field()

    class Meta:
        model = SafetyTask
        fields = ('id', 'title', 'description', 'task_type', 'priority', 'status',
                  'assigned_to', 'assigned_to_name', 'assigned_by', 'assigned_by_name',
                  'department', 'department_name', 'start_date', 'deadline', 'completion_date', 'notes')
        export_order = fields
        import_id_fields = ('id',)
        skip_unchanged = True
        report_skipped = True

    def dehydrate_assigned_to_name(self, task):
        return f"{task.assigned_to.last_name} {task.assigned_to.first_name}" if task.assigned_to else ""

    def dehydrate_assigned_by_name(self, task):
        return f"{task.assigned_by.last_name} {task.assigned_by.first_name}" if task.assigned_by else ""

    def dehydrate_department_name(self, task):
        return task.department.name if task.department else ""

    def before_import_row(self, row, **kwargs):
        """Предварительная обработка строки перед импортом"""
        # Преобразование статусов из русского в английский
        status_mapping = {
            'Новая': 'new',
            'В обработке': 'in_progress',
            'Выполнено': 'completed',
            'Отменено': 'canceled'
        }

        priority_mapping = {
            'Низкий': 'low',
            'Средний': 'medium',
            'Высокий': 'high',
            'Критический': 'critical'
        }

        if 'status' in row and row['status'] in status_mapping:
            row['status'] = status_mapping[row['status']]

        if 'priority' in row and row['priority'] in priority_mapping:
            row['priority'] = priority_mapping[row['priority']]

    def get_or_init_instance(self, instance_loader, row):
        """Получение или создание экземпляра"""
        instance, created = super().get_or_init_instance(instance_loader, row)
        return instance, created

# Ресурс для уведомлений
class NotificationResource(resources.ModelResource):
    user_name = Field()

    class Meta:
        model = Notification
        fields = ('id', 'user__username', 'user_name', 'title', 'message',
                 'notification_type', 'related_entity_type', 'related_entity_id',
                 'is_read', 'created_at')
        export_order = fields

    def dehydrate_user_name(self, notification):
        return f"{notification.user.last_name} {notification.user.first_name}" if notification.user else ""

