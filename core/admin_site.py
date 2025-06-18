from django.contrib import admin
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    Employee, Risk, Instruction, Document, Equipment, Inspection,
    MedicalExamination, Incident, PPERequest, Department, PPEItem, InstructionType, EquipmentMaintenance, Hazard,
    WorkplaceAssessment, SafetyTask, Notification, UserLog
)


class OrionDashboardView(TemplateView):
    template_name = 'admin/orion_dashboard.html'

    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Текущая дата и важные временные точки
        now = timezone.now()
        today = now.date()
        month_ago = today - timedelta(days=30)

        # Количество сотрудников
        context['employees_count'] = Employee.objects.count()

        # Риски по уровням
        risk_levels = Risk.objects.values('level').annotate(count=Count('id'))
        risk_levels_dict = {item['level']: item['count'] for item in risk_levels}
        context['risk_critical'] = risk_levels_dict.get('critical', 0)
        context['risk_high'] = risk_levels_dict.get('high', 0)
        context['risk_medium'] = risk_levels_dict.get('medium', 0)
        context['risk_low'] = risk_levels_dict.get('low', 0)

        # Медосмотры
        context['overdue_medical_exams'] = Employee.objects.filter(
            next_medical_exam_date__lt=today
        ).count()

        context['upcoming_medical_exams'] = Employee.objects.filter(
            next_medical_exam_date__gte=today,
            next_medical_exam_date__lte=today + timedelta(days=30)
        ).count()

        # Оборудование, требующее обслуживания
        context['equipment_requiring_maintenance'] = Equipment.objects.filter(
            Q(status='requires_maintenance') |
            Q(next_maintenance_date__lt=now)
        ).count()

        # Статистика инструктажей за последний месяц
        context['instructions_last_month'] = Instruction.objects.filter(
            instruction_date__gte=month_ago
        ).count()

        # Статистика происшествий за последний месяц
        context['incidents_last_month'] = Incident.objects.filter(
            incident_date__gte=month_ago
        ).count()

        # Инструктажи, у которых истек срок действия
        context['overdue_instructions'] = Instruction.objects.filter(
            next_instruction_date__lt=now
        ).count()

        # Проверки
        inspection_statuses = Inspection.objects.values('status').annotate(count=Count('id'))
        inspection_statuses_dict = {item['status']: item['count'] for item in inspection_statuses}
        context['inspections_new'] = inspection_statuses_dict.get('new', 0)
        context['inspections_in_progress'] = inspection_statuses_dict.get('in_progress', 0)
        context['inspections_completed'] = inspection_statuses_dict.get('completed', 0)

        # Заявки на СИЗ
        ppe_request_statuses = PPERequest.objects.values('status').annotate(count=Count('id'))
        ppe_request_statuses_dict = {item['status']: item['count'] for item in ppe_request_statuses}
        context['ppe_requests_new'] = ppe_request_statuses_dict.get('new', 0)
        context['ppe_requests_in_progress'] = ppe_request_statuses_dict.get('in_progress', 0)
        context['ppe_requests_completed'] = ppe_request_statuses_dict.get('completed', 0)

        # Нарушения
        findings_count = 0
        resolved_findings_count = 0

        for inspection in Inspection.objects.all():
            findings = inspection.findings.all()
            findings_count += findings.count()
            resolved_findings_count += findings.filter(status='completed').count()

        if findings_count > 0:
            context['compliance_percentage'] = int((resolved_findings_count / findings_count) * 100)
        else:
            context['compliance_percentage'] = 100

        # Последний инцидент
        last_incident = Incident.objects.order_by('-incident_date').first()
        if last_incident:
            context['incident_free_days'] = (today - last_incident.incident_date.date()).days
        else:
            context['incident_free_days'] = 365

        # Недавние документы
        context['recent_documents'] = Document.objects.order_by('-updated_at')[:5]

        # Ближайшие инструктажи
        context['upcoming_instructions'] = Instruction.objects.filter(
            next_instruction_date__gte=today
        ).order_by('next_instruction_date')[:5]

        return context


class OrionAdminSite(admin.AdminSite):
    site_header = 'Орион - Система безопасности на рабочем месте'
    site_title = 'Орион'
    index_title = 'Панель администратора'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(OrionDashboardView.as_view()), name='orion_dashboard'),
        ]
        return custom_urls + urls


# Инициализация собственного AdminSite
orion_admin_site = OrionAdminSite(name='orion_admin')

# Импортируем все классы админки из admin.py
from .admin import (
    CustomUserAdmin, DepartmentAdmin, EmployeeAdmin, PPEItemAdmin,
    PPERequestAdmin, DocumentAdmin, InstructionTypeAdmin, InstructionAdmin,
    EquipmentAdmin, EquipmentMaintenanceAdmin, HazardAdmin, RiskAdmin,
    InspectionAdmin, IncidentAdmin, MedicalExaminationAdmin,
    WorkplaceAssessmentAdmin, SafetyTaskAdmin, NotificationAdmin, UserLogAdmin
)

# Импортируем модель User
from django.contrib.auth.models import User

# Регистрируем модели в нашей кастомной админке
orion_admin_site.register(User, CustomUserAdmin)
orion_admin_site.register(Department, DepartmentAdmin)
orion_admin_site.register(Employee, EmployeeAdmin)
orion_admin_site.register(PPEItem, PPEItemAdmin)
orion_admin_site.register(PPERequest, PPERequestAdmin)
orion_admin_site.register(Document, DocumentAdmin)
orion_admin_site.register(InstructionType, InstructionTypeAdmin)
orion_admin_site.register(Instruction, InstructionAdmin)
orion_admin_site.register(Equipment, EquipmentAdmin)
orion_admin_site.register(EquipmentMaintenance, EquipmentMaintenanceAdmin)
orion_admin_site.register(Hazard, HazardAdmin)
orion_admin_site.register(Risk, RiskAdmin)
orion_admin_site.register(Inspection, InspectionAdmin)
orion_admin_site.register(Incident, IncidentAdmin)
orion_admin_site.register(MedicalExamination, MedicalExaminationAdmin)
orion_admin_site.register(WorkplaceAssessment, WorkplaceAssessmentAdmin)
orion_admin_site.register(SafetyTask, SafetyTaskAdmin)
orion_admin_site.register(Notification, NotificationAdmin)
orion_admin_site.register(UserLog, UserLogAdmin)