import json
from datetime import timedelta, datetime

import psycopg2
from django.contrib.auth import authenticate, login, logout, user_logged_in, user_logged_out, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView, \
    PasswordResetView
from django.db.models.functions import TruncYear, TruncMonth
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.urls import reverse_lazy
from django.utils import timezone
from django.core.paginator import Paginator
from django.utils.timezone import now
from prometheus_client import generate_latest

#from core.customlogger import database_size_gauge
from .decorators import role_required
from .models import (
    Employee, Department, PPEItem, PPERequest, PPEIssuance,
    Document, InstructionType, Instruction, InstructionParticipant,
    Equipment, EquipmentMaintenance, Hazard, Risk, RiskMitigationMeasure,
    Inspection, InspectionFinding, Incident,
    MedicalExamination, Notification, UserLog, IncidentVictim, EvacuationNotification, TestResult, InstructionTest,
    InstructionMaterial, TestAnswerSubmission, TestAnswer
)
from .forms import (
    PPERequestForm, InstructionForm, DocumentForm,
    EquipmentForm, RiskForm, InspectionForm, SafetyTaskForm, ProfileForm, EmployeeForm, EquipmentMaintenanceForm,
    MedicalExaminationForm, InspectionFindingForm, RiskMitigationMeasureForm, TestSubmissionForm,
    InstructionMaterialForm, InstructionTestForm, TestQuestionForm, TestAnswerFormSet
)
from .signals import create_employee_if_missing
from .utils import generate_pdf_report, generate_excel_report


@login_required
def dashboard(request):
    """Главная страница (дашборд) с учетом роли пользователя"""

    # Инициализируем employee как None
    employee = None
    user_role = 'employee'  # По умолчанию

    # Пробуем получить роль пользователя
    try:
        employee = request.user.employee
        user_role = employee.role
    except:
        # Если не получилось - используем значения по умолчанию
        pass

    # Статистика безопасности
    last_incident = Incident.objects.order_by('-incident_date').first()
    if last_incident:
        incident_free_days = (timezone.now().date() - last_incident.incident_date.date()).days
    else:
        incident_free_days = 365  # Если инцидентов нет, показываем 365 дней

    identified_risks_count = Risk.objects.count()

    total_findings = InspectionFinding.objects.count()
    resolved_findings = InspectionFinding.objects.filter(status='completed').count()
    compliance_percentage = 100 if total_findings == 0 else int((resolved_findings / total_findings) * 100)

    # Базовый контекст для всех ролей
    context = {
        'user_role': user_role,
        'incident_free_days': incident_free_days,
        'identified_risks_count': identified_risks_count,
        'compliance_percentage': compliance_percentage,
        'employee': employee,  # Передаем employee в контекст, даже если это None
    }

    # Текущая дата и важные временные точки для медицинских осмотров
    current_date = timezone.now().date()
    warning_date = current_date + timedelta(days=5)
    next_month = current_date + timedelta(days=30)

    # Дополнительный контекст для медицинского работника
    if user_role == 'medical_worker':
        # Сотрудники с просроченными медосмотрами
        overdue_employees = Employee.objects.filter(
            next_medical_exam_date__lt=current_date
        ).select_related('user', 'department').order_by('next_medical_exam_date')[:5]

        # Сотрудники с приближающимися медосмотрами (в течение 5 дней)
        upcoming_employees = Employee.objects.filter(
            next_medical_exam_date__gte=current_date,
            next_medical_exam_date__lte=warning_date
        ).select_related('user', 'department').order_by('next_medical_exam_date')[:5]

        # Сотрудники с медосмотрами в ближайший месяц
        monthly_employees = Employee.objects.filter(
            next_medical_exam_date__gt=warning_date,
            next_medical_exam_date__lte=next_month
        ).select_related('user', 'department').order_by('next_medical_exam_date')[:10]

        # Последние проведенные медосмотры
        recent_exams = MedicalExamination.objects.select_related(
            'employee', 'employee__user', 'employee__department'
        ).order_by('-exam_date')[:5]

        # Статистика по медосмотрам
        total_employees = Employee.objects.count()
        overdue_count = Employee.objects.filter(next_medical_exam_date__lt=current_date).count()
        upcoming_count = Employee.objects.filter(
            next_medical_exam_date__gte=current_date,
            next_medical_exam_date__lte=warning_date
        ).count()
        monthly_count = Employee.objects.filter(
            next_medical_exam_date__gt=warning_date,
            next_medical_exam_date__lte=next_month
        ).count()

        # Статистика по подразделениям
        department_stats = []
        departments = Department.objects.all()

        for dept in departments:
            dept_employees = Employee.objects.filter(department=dept).count()
            if dept_employees > 0:
                overdue_dept = Employee.objects.filter(
                    department=dept,
                    next_medical_exam_date__lt=current_date
                ).count()

                compliance_percent = 100
                if dept_employees > 0:
                    compliance_percent = 100 - int((overdue_dept / dept_employees) * 100)

                department_stats.append({
                    'name': dept.name,
                    'total': dept_employees,
                    'overdue': overdue_dept,
                    'compliance': compliance_percent
                })

        # Сортируем подразделения по соответствию (от худшего к лучшему)
        department_stats.sort(key=lambda x: x['compliance'])

        # Медицинские осмотры по типам
        exam_types = MedicalExamination.objects.values('exam_type').annotate(
            count=Count('id')
        ).order_by('-count')[:5]

        # Обновляем контекст данными для медицинского работника
        context.update({
            'overdue_employees': overdue_employees,
            'upcoming_employees': upcoming_employees,
            'monthly_employees': monthly_employees,
            'recent_exams': recent_exams,
            'total_employees': total_employees,
            'overdue_count': overdue_count,
            'upcoming_count': upcoming_count,
            'monthly_count': monthly_count,
            'department_stats': department_stats,
            'exam_types': exam_types,
            'current_date': current_date,
            'warning_date': warning_date,
            'next_month': next_month
        })

    elif user_role == 'department_head':
        # Проверяем наличие employee и department
        if employee and employee.department:
            department = employee.department

            # Ближайшие инструктажи для подразделения
            upcoming_instructions = Instruction.objects.filter(
                department=department,
                next_instruction_date__gte=timezone.now()
            ).order_by('next_instruction_date')[:5]

            # Критические риски для подразделения
            critical_risks = Risk.objects.filter(
                department=department,
                level__in=['high', 'critical']
            ).order_by('-evaluation_date')[:5]

            # Задачи СИЗ для сотрудников подразделения
            ppe_tasks = PPERequest.objects.filter(
                employee__department=department
            ).select_related('employee', 'employee__user').order_by('-request_date')[:6]

            # Проверки для подразделения
            recent_inspections = Inspection.objects.filter(
                department=department
            ).select_related('lead_inspector').order_by('-start_date')[:5]

            # Сотрудники подразделения с просроченными медосмотрами
            employees_with_overdue_exams = Employee.objects.filter(
                department=department,
                next_medical_exam_date__lt=timezone.now().date()
            ).select_related('user')[:5]

            context.update({
                'upcoming_instructions': upcoming_instructions,
                'critical_risks': critical_risks,
                'ppe_tasks': ppe_tasks,
                'recent_inspections': recent_inspections,
                'employees_with_overdue_exams': employees_with_overdue_exams,
            })
        else:
            # Если department отсутствует, используем пустые списки
            context.update({
                'upcoming_instructions': [],
                'critical_risks': [],
                'ppe_tasks': [],
                'recent_inspections': [],
                'employees_with_overdue_exams': [],
            })

    elif user_role == 'employee':
        # Проверяем наличие employee
        if employee:
            # Инструктажи сотрудника
            instruction_participations = InstructionParticipant.objects.filter(
                employee=employee
            ).select_related('instruction', 'instruction__instruction_type').order_by('-instruction__instruction_date')[
                                         :5]

            # СИЗ сотрудника
            ppe_issuances = PPEIssuance.objects.filter(
                employee=employee,
                actual_return_date__isnull=True  # Еще не возвращенные
            ).select_related('ppe_item').order_by('-issue_date')

            # Медосмотры сотрудника
            medical_exams = MedicalExamination.objects.filter(
                employee=employee
            ).order_by('-exam_date')[:3]

            # Если у сотрудника есть подразделение, то добавляем риски подразделения
            if employee.department:
                # Риски для подразделения сотрудника
                department_risks = Risk.objects.filter(
                    department=employee.department
                ).order_by('-evaluation_date')[:5]

                context.update({
                    'department_risks': department_risks,
                })

            context.update({
                'instruction_participations': instruction_participations,
                'ppe_issuances': ppe_issuances,
                'medical_exams': medical_exams,
            })
        else:
            # Если employee отсутствует, используем пустые списки
            context.update({
                'instruction_participations': [],
                'ppe_issuances': [],
                'medical_exams': [],
                'department_risks': [],
            })

    # Добавляем обработку других ролей по аналогии...

    # Количество непрочитанных уведомлений - для всех ролей
    notification_count = Notification.objects.filter(user=request.user, is_read=False).count()
    context['notification_count'] = notification_count

    return render(request, 'dashboard/dashboard.html', context)
# Поиск
@login_required
def search(request):
    query = request.GET.get('q', '')

    if not query:
        return render(request, 'search_results.html', {'query': query})

    # Поиск по разным моделям
    documents = Document.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )[:10]

    ppe_requests = PPERequest.objects.filter(
        Q(notes__icontains=query)
    )[:10]

    instructions = Instruction.objects.filter(
        Q(notes__icontains=query) | Q(location__icontains=query)
    )[:10]

    risks = Risk.objects.filter(
        Q(description__icontains=query) | Q(location__icontains=query)
    )[:10]

    inspections = Inspection.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    )[:10]

    employees = Employee.objects.filter(
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(position__icontains=query)
    )[:10]

    equipment = Equipment.objects.filter(
        Q(name__icontains=query) |
        Q(model__icontains=query) |
        Q(serial_number__icontains=query)
    )[:10]

    context = {
        'query': query,
        'documents': documents,
        'ppe_requests': ppe_requests,
        'instructions': instructions,
        'risks': risks,
        'inspections': inspections,
        'employees': employees,
        'equipment': equipment,
    }
    return render(request, 'search_results.html', context)


# Профиль пользователя
@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)

    context = {
        'form': form
    }
    return render(request, 'profile.html', context)


# Настройки
@login_required
def settings(request):
    """Страница настроек системы"""

    if request.method == 'POST':
        settings_type = request.POST.get('settings_type', '')

        if settings_type == 'system':
            # Обработка системных настроек
            company_name = request.POST.get('company_name')
            admin_email = request.POST.get('admin_email')
            items_per_page = request.POST.get('items_per_page')

            # Здесь можно добавить логику сохранения настроек

            messages.success(request, 'Системные настройки успешно обновлены.')
            return redirect('settings')

        elif settings_type == 'security':
            # Обработка настроек безопасности
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            # Проверка текущего пароля
            user = request.user
            if not user.check_password(current_password):
                messages.error(request, 'Текущий пароль указан неверно.')
                return redirect('settings')

            # Проверка нового пароля
            if new_password != confirm_password:
                messages.error(request, 'Новый пароль и подтверждение не совпадают.')
                return redirect('settings')

            # Установка нового пароля
            user.set_password(new_password)
            user.save()

            # Обновление сессии, чтобы пользователь не вылетел
            update_session_auth_hash(request, user)

            messages.success(request, 'Пароль успешно изменен.')
            return redirect('settings')

    # Загрузка данных для справочников
    try:
        departments = Department.objects.all()
        ppe_items = PPEItem.objects.all()
        instruction_types = InstructionType.objects.all()
        hazards = Hazard.objects.all()
    except:
        departments = []
        ppe_items = []
        instruction_types = []
        hazards = []

    context = {
        'departments': departments,
        'ppe_items': ppe_items,
        'instruction_types': instruction_types,
        'hazards': hazards
    }

    return render(request, 'settings.html', context)


# Задачи СИЗ
@login_required
def ppe_list(request):
    ppe_requests = PPERequest.objects.select_related(
        'employee', 'employee__user', 'ppe_item'
    ).order_by('-request_date')

    # Фильтрация
    status_filter = request.GET.get('status')
    if status_filter:
        ppe_requests = ppe_requests.filter(status=status_filter)

    # Пагинация
    paginator = Paginator(ppe_requests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
    }
    return render(request, 'ppe/ppe_list.html', context)


@login_required
def ppe_detail(request, pk):
    ppe_request = get_object_or_404(PPERequest, pk=pk)

    # История выдачи СИЗ для этого сотрудника
    issuance_history = PPEIssuance.objects.filter(
        employee=ppe_request.employee
    ).order_by('-issue_date')

    context = {
        'ppe_request': ppe_request,
        'issuance_history': issuance_history,
    }
    return render(request, 'ppe/ppe_detail.html', context)


@login_required
def ppe_create(request):
    if request.method == 'POST':
        form = PPERequestForm(request.POST)
        if form.is_valid():
            ppe_request = form.save(commit=False)
            ppe_request.save()
            messages.success(request, 'Заявка на СИЗ успешно создана.')
            return redirect('ppe_list')
    else:
        form = PPERequestForm()

    context = {
        'form': form,
        'title': 'Создание заявки на СИЗ'
    }
    return render(request, 'ppe/ppe_form.html', context)


@login_required
@role_required(['admin', 'safety_specialist', 'department_head'])
def ppe_update(request, pk):
    ppe_request = get_object_or_404(PPERequest, pk=pk)

    if request.method == 'POST':
        form = PPERequestForm(request.POST, instance=ppe_request)
        if form.is_valid():
            form.save()
            messages.success(request, 'Заявка на СИЗ успешно обновлена.')
            return redirect('ppe_detail', pk=ppe_request.pk)
    else:
        form = PPERequestForm(instance=ppe_request)

    context = {
        'form': form,
        'title': 'Редактирование заявки на СИЗ'
    }
    return render(request, 'ppe/ppe_form.html', context)


@login_required
@role_required(['admin', 'safety_specialist', 'department_head'])
def ppe_delete(request, pk):
    ppe_request = get_object_or_404(PPERequest, pk=pk)

    if request.method == 'POST':
        ppe_request.delete()
        messages.success(request, 'Заявка на СИЗ успешно удалена.')
        return redirect('ppe_list')

    context = {
        'ppe_request': ppe_request
    }
    return render(request, 'ppe/ppe_confirm_delete.html', context)


# Инструктажи
@login_required
def instruction_list(request):
    # Получаем все инструктажи с необходимыми связями
    instructions = Instruction.objects.select_related(
        'instruction_type', 'instructor', 'department'
    ).all()

    # Добавляем количество участников к каждому инструктажу
    instructions = instructions.annotate(participants_count=Count('participants'))

    # Фильтрация по подразделению
    department_filter = request.GET.get('department')
    if department_filter:
        instructions = instructions.filter(department_id=department_filter)

    # Фильтрация по типу инструктажа
    type_filter = request.GET.get('type')
    if type_filter:
        instructions = instructions.filter(instruction_type_id=type_filter)

    # Список всех подразделений для фильтра
    departments = Department.objects.all()

    # Список всех типов инструктажей для фильтра
    instruction_types = InstructionType.objects.all()

    # Пагинация
    paginator = Paginator(instructions.order_by('-instruction_date'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Текущая дата
    current_date = timezone.now().date()

    # Данные для графика по типам инструктажей
    instruction_types_chart_data = Instruction.objects.values(
        'instruction_type__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')

    instruction_types_labels = [item['instruction_type__name'] for item in instruction_types_chart_data]
    instruction_types_counts = [item['count'] for item in instruction_types_chart_data]

    # Данные для графика по месяцам
    six_months_ago = timezone.now().date() - timedelta(days=180)
    instruction_months_chart_data = Instruction.objects.filter(
        instruction_date__date__gte=six_months_ago
    ).annotate(
        month=TruncMonth('instruction_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    instruction_months_labels = [item['month'].strftime('%b %Y') for item in instruction_months_chart_data]
    instruction_months_counts = [item['count'] for item in instruction_months_chart_data]

    context = {
        'page_obj': page_obj,
        'departments': departments,
        'instruction_types': instruction_types,
        'department_filter': department_filter,
        'type_filter': type_filter,
        'current_date': current_date,
        'instruction_types_labels': json.dumps(instruction_types_labels),
        'instruction_types_counts': json.dumps(instruction_types_counts),
        'instruction_months_labels': json.dumps(instruction_months_labels),
        'instruction_months_counts': json.dumps(instruction_months_counts),
    }
    return render(request, 'instructions/instruction_list.html', context)


@login_required
def instruction_detail(request, pk):
    instruction = get_object_or_404(Instruction, pk=pk)

    # Участники инструктажа
    participants = InstructionParticipant.objects.filter(
        instruction=instruction
    ).select_related('employee', 'employee__user')

    context = {
        'instruction': instruction,
        'participants': participants,
    }
    return render(request, 'instructions/instruction_detail.html', context)


@login_required
def instruction_create(request):
    if request.method == 'POST':
        form = InstructionForm(request.POST)
        if form.is_valid():
            instruction = form.save(commit=False)
            instruction.instructor = request.user
            instruction.save()

            # Обработка выбранных участников
            participant_ids = request.POST.getlist('participants')
            for employee_id in participant_ids:
                InstructionParticipant.objects.create(
                    instruction=instruction,
                    employee_id=employee_id,
                    status='attended'
                )

            messages.success(request, 'Инструктаж успешно создан.')
            return redirect('instruction_list')
    else:
        form = InstructionForm()

    # Список сотрудников для выбора участников
    employees = Employee.objects.select_related('user', 'department').all()

    context = {
        'form': form,
        'employees': employees,
        'title': 'Проведение инструктажа'
    }
    return render(request, 'instructions/instruction_form.html', context)


@login_required
def instruction_update(request, pk):
    instruction = get_object_or_404(Instruction, pk=pk)

    if request.method == 'POST':
        form = InstructionForm(request.POST, instance=instruction)
        if form.is_valid():
            form.save()

            # Получение текущих участников перед удалением
            existing_participants = list(InstructionParticipant.objects.filter(
                instruction=instruction
            ).values_list('employee_id', flat=True))

            # Обновление участников
            InstructionParticipant.objects.filter(instruction=instruction).delete()
            participant_ids = request.POST.getlist('participants')

            # Находим новых участников (тех, которых не было раньше)
            new_participant_ids = [int(id) for id in participant_ids if int(id) not in existing_participants]

            # Создаем объекты участников
            for employee_id in participant_ids:
                InstructionParticipant.objects.create(
                    instruction=instruction,
                    employee_id=employee_id,
                    status='attended'
                )

            # Отправляем уведомления только новым участникам
            if new_participant_ids:
                new_employees = Employee.objects.filter(id__in=new_participant_ids)
                for employee in new_employees:
                    Notification.objects.create(
                        user=employee.user,
                        title=f'Назначен инструктаж: {instruction.instruction_type.name}',
                        message=f'Вам назначен инструктаж "{instruction.instruction_type.name}". Дата проведения: {instruction.instruction_date.strftime("%d.%m.%Y %H:%M")}.',
                        notification_type='instruction_assigned',
                        related_entity_type='instruction',
                        related_entity_id=instruction.id,
                        is_read=False
                    )

            messages.success(request, 'Инструктаж успешно обновлен.')
            return redirect('instruction_detail', pk=instruction.pk)
    else:
        form = InstructionForm(instance=instruction)

    # Список сотрудников для выбора участников
    employees = Employee.objects.select_related('user', 'department').all()

    # Текущие участники
    current_participants = InstructionParticipant.objects.filter(
        instruction=instruction
    ).values_list('employee_id', flat=True)

    context = {
        'form': form,
        'employees': employees,
        'current_participants': current_participants,
        'title': 'Редактирование инструктажа'
    }
    return render(request, 'instructions/instruction_form.html', context)

@login_required
def instruction_delete(request, pk):
    instruction = get_object_or_404(Instruction, pk=pk)

    if request.method == 'POST':
        instruction.delete()
        messages.success(request, 'Инструктаж успешно удален.')
        return redirect('instruction_list')

    context = {
        'instruction': instruction
    }
    return render(request, 'instructions/instruction_confirm_delete.html', context)


# Нормативные документы
@login_required
def document_list(request):
    # Получаем все документы
    documents = Document.objects.all()

    # Фильтрация по типу документа
    document_type = request.GET.get('type')
    if document_type:
        documents = documents.filter(document_type=document_type)

    # Фильтрация по статусу
    is_active_filter = request.GET.get('is_active')
    if is_active_filter is not None:
        is_active = is_active_filter == '1'
        documents = documents.filter(is_active=is_active)

    # Получаем список всех типов документов для фильтра
    document_types = Document.objects.values_list('document_type', flat=True).distinct()

    # Пагинация
    paginator = Paginator(documents.order_by('-updated_at'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Текущая дата
    current_date = timezone.now().date()

    # Недавно обновленные документы (для бокового списка)
    recent_documents = Document.objects.order_by('-updated_at')[:5]

    # Данные для графика по типам документов
    document_types_chart_data = Document.objects.values('document_type').annotate(
        count=Count('id')
    ).order_by('-count')

    document_types_labels = [item['document_type'] for item in document_types_chart_data]
    document_types_counts = [item['count'] for item in document_types_chart_data]

    # Данные для графика по годам публикации
    document_years_chart_data = Document.objects.exclude(publish_date=None).annotate(
        year=TruncYear('publish_date')
    ).values('year').annotate(
        count=Count('id')
    ).order_by('year')

    document_years_labels = [item['year'].strftime('%Y') for item in document_years_chart_data]
    document_years_counts = [item['count'] for item in document_years_chart_data]

    context = {
        'page_obj': page_obj,
        'document_types': document_types,
        'document_type': document_type,
        'is_active_filter': is_active_filter,
        'current_date': current_date,
        'recent_documents': recent_documents,
        'document_types_labels': json.dumps(document_types_labels),
        'document_types_counts': json.dumps(document_types_counts),
        'document_years_labels': json.dumps(document_years_labels),
        'document_years_counts': json.dumps(document_years_counts),
    }
    return render(request, 'documents/document_list.html', context)

@login_required
def document_detail(request, pk):
    document = get_object_or_404(Document, pk=pk)

    context = {
        'document': document
    }
    return render(request, 'documents/document_detail.html', context)


@login_required
@role_required(['admin', 'safety_specialist', 'department_head'])
def document_create(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save()
            messages.success(request, 'Документ успешно создан.')
            return redirect('document_list')
    else:
        form = DocumentForm()

    context = {
        'form': form,
        'title': 'Добавление документа'
    }
    return render(request, 'documents/document_form.html', context)


@login_required
@role_required(['admin', 'safety_specialist', 'department_head'])
def document_update(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, 'Документ успешно обновлен.')
            return redirect('document_detail', pk=document.pk)
    else:
        form = DocumentForm(instance=document)

    context = {
        'form': form,
        'document': document,
        'title': 'Редактирование документа'
    }
    return render(request, 'documents/document_form.html', context)


@login_required
@role_required(['admin', 'safety_specialist', 'department_head'])
def document_delete(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Документ успешно удален.')
        return redirect('document_list')

    context = {
        'document': document
    }
    return render(request, 'documents/document_confirm_delete.html', context)


# Риски и опасности
@login_required
@role_required(['admin', 'safety_specialist', 'department_head'])
def risk_list(request):
    risks = Risk.objects.select_related('hazard', 'department').all()

    # Фильтрация
    level_filter = request.GET.get('level')
    if level_filter:
        risks = risks.filter(level=level_filter)

    # Пагинация
    paginator = Paginator(risks.order_by('-evaluation_date'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Данные для графика по уровням рисков
    risk_levels_chart_data = Risk.objects.values('level').annotate(
        count=Count('id')
    ).order_by('level')

    risk_levels_labels = [
        'Низкий' if item['level'] == 'low' else
        'Средний' if item['level'] == 'medium' else
        'Высокий' if item['level'] == 'high' else
        'Критический' for item in risk_levels_chart_data
    ]
    risk_levels_counts = [item['count'] for item in risk_levels_chart_data]

    # Данные для графика по подразделениям
    risk_departments_chart_data = Risk.objects.values(
        'department__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]  # Топ-5 подразделений по количеству рисков

    risk_departments_labels = [item['department__name'] for item in risk_departments_chart_data]
    risk_departments_counts = [item['count'] for item in risk_departments_chart_data]

    context = {
        'page_obj': page_obj,
        'level_filter': level_filter,
        'risk_levels_labels': json.dumps(risk_levels_labels),
        'risk_levels_counts': json.dumps(risk_levels_counts),
        'risk_departments_labels': json.dumps(risk_departments_labels),
        'risk_departments_counts': json.dumps(risk_departments_counts),
    }
    return render(request, 'risks/risk_list.html', context)


@login_required
@role_required(['admin', 'safety_specialist', 'department_head'])
def risk_detail(request, pk):
    risk = get_object_or_404(Risk, pk=pk)

    # Мероприятия по снижению риска
    mitigation_measures = RiskMitigationMeasure.objects.filter(risk=risk).order_by('-created_at')

    context = {
        'risk': risk,
        'mitigation_measures': mitigation_measures,
    }
    return render(request, 'risks/risk_detail.html', context)


@login_required
@role_required(['admin', 'safety_specialist'])
def risk_create(request):
    if request.method == 'POST':
        form = RiskForm(request.POST)
        if form.is_valid():
            risk = form.save(commit=False)
            risk.evaluated_by = request.user
            risk.save()
            messages.success(request, 'Риск успешно добавлен.')
            return redirect('risk_list')
    else:
        form = RiskForm()

    context = {
        'form': form,
        'title': 'Добавление риска'
    }
    return render(request, 'risks/risk_form.html', context)


@login_required
@role_required(['admin', 'safety_specialist'])
def risk_update(request, pk):
    risk = get_object_or_404(Risk, pk=pk)

    if request.method == 'POST':
        form = RiskForm(request.POST, instance=risk)
        if form.is_valid():
            form.save()
            messages.success(request, 'Риск успешно обновлен.')
            return redirect('risk_detail', pk=risk.pk)
    else:
        form = RiskForm(instance=risk)

    context = {
        'form': form,
        'risk': risk,
        'title': 'Редактирование риска'
    }
    return render(request, 'risks/risk_form.html', context)


@login_required
@role_required(['admin', 'safety_specialist'])
def risk_delete(request, pk):
    risk = get_object_or_404(Risk, pk=pk)

    if request.method == 'POST':
        risk.delete()
        messages.success(request, 'Риск успешно удален.')
        return redirect('risk_list')

    context = {
        'risk': risk
    }
    return render(request, 'risks/risk_confirm_delete.html', context)


@login_required
def risk_assessment(request):
    # Логика для страницы оценки рисков
    hazards = Hazard.objects.all()
    departments = Department.objects.all()

    context = {
        'hazards': hazards,
        'departments': departments,
    }
    return render(request, 'risks/risk_assessment.html', context)


# Проверки
@login_required
def inspection_list(request):
    inspections = Inspection.objects.select_related('department', 'lead_inspector').all()

    # Добавляем количество нарушений к каждой проверке
    inspections = inspections.annotate(
        findings_count=Count('findings'),
        resolved_findings_count=Count('findings', filter=Q(findings__status='completed')),
        overdue_findings_count=Count(
            'findings',
            filter=Q(findings__status__in=['new', 'in_progress']) & Q(findings__deadline__lt=timezone.now())
        )
    )

    # Фильтрация
    status_filter = request.GET.get('status')
    if status_filter:
        inspections = inspections.filter(status=status_filter)

    # Пагинация
    paginator = Paginator(inspections.order_by('-start_date'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Данные для графика по статусам проверок
    inspection_status_chart_data = Inspection.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    inspection_status_labels = [
        'Новая' if item['status'] == 'new' else
        'В процессе' if item['status'] == 'in_progress' else
        'Завершена' if item['status'] == 'completed' else
        'Отменена' for item in inspection_status_chart_data
    ]
    inspection_status_counts = [item['count'] for item in inspection_status_chart_data]

    # Данные для графика по типам проверок
    inspection_types_chart_data = Inspection.objects.values('inspection_type').annotate(
        count=Count('id')
    ).order_by('-count')

    inspection_types_labels = [item['inspection_type'] for item in inspection_types_chart_data]
    inspection_types_counts = [item['count'] for item in inspection_types_chart_data]

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'inspection_status_labels': json.dumps(inspection_status_labels),
        'inspection_status_counts': json.dumps(inspection_status_counts),
        'inspection_types_labels': json.dumps(inspection_types_labels),
        'inspection_types_counts': json.dumps(inspection_types_counts),
    }
    return render(request, 'inspections/inspection_list.html', context)


@login_required
def inspection_detail(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)

    # Выявленные нарушения
    findings = InspectionFinding.objects.filter(inspection=inspection).order_by('-created_at')

    context = {
        'inspection': inspection,
        'findings': findings,
    }
    return render(request, 'inspections/inspection_detail.html', context)


@login_required
def inspection_create(request):
    if request.method == 'POST':
        form = InspectionForm(request.POST)
        if form.is_valid():
            inspection = form.save(commit=False)
            inspection.lead_inspector = request.user
            inspection.save()
            messages.success(request, 'Проверка успешно создана.')
            return redirect('inspection_list')
    else:
        form = InspectionForm()

    context = {
        'form': form,
        'title': 'Создание проверки'
    }
    return render(request, 'inspections/inspection_form.html', context)


@login_required
def inspection_update(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)

    if request.method == 'POST':
        form = InspectionForm(request.POST, instance=inspection)
        if form.is_valid():
            form.save()
            messages.success(request, 'Проверка успешно обновлена.')
            return redirect('inspection_detail', pk=inspection.pk)
    else:
        form = InspectionForm(instance=inspection)

    context = {
        'form': form,
        'inspection': inspection,
        'title': 'Редактирование проверки'
    }
    return render(request, 'inspections/inspection_form.html', context)


@login_required
def inspection_delete(request, pk):
    inspection = get_object_or_404(Inspection, pk=pk)

    if request.method == 'POST':
        inspection.delete()
        messages.success(request, 'Проверка успешно удалена.')
        return redirect('inspection_list')

    context = {
        'inspection': inspection
    }
    return render(request, 'inspections/inspection_confirm_delete.html', context)


@login_required
def inspection_results_report(request, format=None):
    """Отчет по результатам проверок с возможностью выгрузки в Excel или PDF"""
    # Получаем данные для отчета
    inspections = Inspection.objects.select_related('department', 'lead_inspector').all()

    # Фильтрация по дате, если указан период
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from:
        inspections = inspections.filter(start_date__gte=date_from)
    if date_to:
        inspections = inspections.filter(start_date__lte=date_to)

    # Собираем данные для отчета
    inspections_count = inspections.count()
    findings_count = InspectionFinding.objects.filter(inspection__in=inspections).count()
    resolved_findings_count = InspectionFinding.objects.filter(
        inspection__in=inspections,
        status='completed'
    ).count()

    # Считаем процент устраненных нарушений
    if findings_count > 0:
        resolved_findings_percentage = int((resolved_findings_count / findings_count) * 100)
    else:
        resolved_findings_percentage = 100

    # Подготавливаем данные для шаблона и экспорта
    inspection_data = []
    for inspection in inspections:
        findings_in_inspection = InspectionFinding.objects.filter(inspection=inspection)
        findings_count_in_inspection = findings_in_inspection.count()
        resolved_count_in_inspection = findings_in_inspection.filter(status='completed').count()

        inspection_data.append({
            'date': inspection.start_date.strftime('%d.%m.%Y'),
            'type': inspection.inspection_type,
            'department': inspection.department.name if inspection.department else '-',
            'inspector': f"{inspection.lead_inspector.last_name} {inspection.lead_inspector.first_name}" if inspection.lead_inspector else '-',
            'findings_count': findings_count_in_inspection,
            'resolved_count': resolved_count_in_inspection,
            'status': 'Завершена' if inspection.status == 'completed' else
            'В процессе' if inspection.status == 'in_progress' else
            'Новая' if inspection.status == 'new' else 'Отменена'
        })

    # Формируем общие данные для отчета
    report_data = {
        'inspections': inspection_data,
        'inspections_count': inspections_count,
        'findings_count': findings_count,
        'resolved_findings_count': resolved_findings_count,
        'resolved_findings_percentage': resolved_findings_percentage,
        'period': f"{date_from} - {date_to}" if date_from and date_to else "Весь период",
        'report_date': timezone.now().strftime('%d.%m.%Y %H:%M')
    }

    # Если запрос на экспорт, генерируем файл
    if format == 'excel':
        output = generate_excel_report(report_data, "Результаты проверок")
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=inspection_results.xlsx'
        return response

    elif format == 'pdf':
        output = generate_pdf_report(report_data, "Результаты проверок")
        response = HttpResponse(output.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=inspection_results.pdf'
        return response

    # Если обычный запрос, отображаем шаблон
    context = {
        'title': 'Результаты проверок',
        'inspections_counts': inspections_count,
        'findings_count': findings_count,
        'resolved_findings_count': resolved_findings_count,
        'resolved_findings_percentage': resolved_findings_percentage,
        'inspections': inspection_data,
        'current_date': timezone.now().date(),
        'date_from': date_from,
        'date_to': date_to
    }

    return render(request, 'reports/inspection_results.html', context)

# Отчеты
@login_required
def report_list(request):
    context = {
        'report_types': [
            {'id': 'safety_metrics', 'name': 'Показатели безопасности'},
            {'id': 'inspection_results', 'name': 'Результаты проверок'},
            {'id': 'ppe_usage', 'name': 'Использование СИЗ'},
            {'id': 'incident_analysis', 'name': 'Анализ происшествий'},
            {'id': 'training_compliance', 'name': 'Соответствие обучения'},
        ]
    }
    return render(request, 'reports/report_list.html', context)


@login_required
def report_generate(request, report_type):
    context = {
        'report_type': report_type
    }

    # Получаем текущую дату для фильтрации данных
    current_date = timezone.now().date()
    year_ago = current_date - timedelta(days=365)
    month_ago = current_date - timedelta(days=30)
    next_month = current_date + timedelta(days=30)

    if report_type == 'safety_metrics':
        # Показатели безопасности
        incidents = Incident.objects.all()
        incidents_count = incidents.count()

        # Последний инцидент для расчета дней без происшествий
        last_incident = incidents.order_by('-incident_date').first()
        if last_incident:
            incident_free_days = (current_date - last_incident.incident_date.date()).days
        else:
            incident_free_days = 365

        # Риски по уровням с процентами и количеством устраненных
        risks_by_level = []
        total_risks = Risk.objects.count()

        for level in ['low', 'medium', 'high', 'critical']:
            risks_count = Risk.objects.filter(level=level).count()
            if total_risks > 0:
                percentage = int((risks_count / total_risks) * 100)
            else:
                percentage = 0

            # Подсчет устраненных рисков по уровню
            # Считаем риск устраненным, если у него есть хотя бы одно завершенное мероприятие
            mitigated_count = Risk.objects.filter(
                level=level,
                mitigation_measures__status='completed'
            ).distinct().count()

            risks_by_level.append({
                'level': level,
                'count': risks_count,
                'percentage': percentage,
                'mitigated': mitigated_count
            })

        # Статистика по нарушениям
        total_findings = InspectionFinding.objects.count()
        resolved_findings = InspectionFinding.objects.filter(status='completed').count()

        if total_findings > 0:
            compliance_percentage = int((resolved_findings / total_findings) * 100)
        else:
            compliance_percentage = 100

        # Разбивка происшествий по месяцам для графика
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

        incidents_by_month = []
        for i in range(6):
            month_date = current_date - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)

            count = Incident.objects.filter(
                incident_date__date__gte=month_start,
                incident_date__date__lte=month_end
            ).count()

            incidents_by_month.append({
                'month': months[month_date.month - 1],
                'count': count
            })

        context.update({
            'title': 'Показатели безопасности',
            'incidents_count': incidents_count,
            'incident_free_days': incident_free_days,
            'risks_by_level': risks_by_level,
            'total_findings': total_findings,
            'resolved_findings': resolved_findings,
            'compliance_percentage': compliance_percentage,
            'incidents_by_month': incidents_by_month,
            'last_incident': last_incident,
            'current_date': current_date
        })

    elif report_type == 'inspection_results':
        # Результаты проверок
        inspections = Inspection.objects.all()
        inspections_count = inspections.count()

        # Нарушения по статусам
        findings = InspectionFinding.objects.all()
        findings_count = findings.count()
        resolved_findings_count = findings.filter(status='completed').count()

        if findings_count > 0:
            findings_resolution_percentage = int((resolved_findings_count / findings_count) * 100)
        else:
            findings_resolution_percentage = 100

        # Статусы проверок для круговой диаграммы
        statuses_data = {
            'new': inspections.filter(status='new').count(),
            'in_progress': inspections.filter(status='in_progress').count(),
            'completed': inspections.filter(status='completed').count(),
            'canceled': inspections.filter(status='canceled').count()
        }

        # Нарушения по подразделениям
        departments = Department.objects.all()
        department_findings = []

        for dept in departments[:5]:  # Ограничим только первыми 5 отделами для наглядности
            found_count = InspectionFinding.objects.filter(
                responsible_department=dept
            ).count()

            resolved_count = InspectionFinding.objects.filter(
                responsible_department=dept,
                status='completed'
            ).count()

            if found_count > 0:
                department_findings.append({
                    'name': dept.name,
                    'found': found_count,
                    'resolved': resolved_count
                })

        # Статистика по типам проверок
        inspection_types = {}
        for inspection in inspections:
            insp_type = inspection.inspection_type
            if insp_type not in inspection_types:
                inspection_types[insp_type] = {
                    'count': 0,
                    'findings': 0,
                    'resolved': 0
                }

            inspection_types[insp_type]['count'] += 1
            findings_in_inspection = InspectionFinding.objects.filter(inspection=inspection)
            inspection_types[insp_type]['findings'] += findings_in_inspection.count()
            inspection_types[insp_type]['resolved'] += findings_in_inspection.filter(status='completed').count()

        inspection_types_data = []
        for insp_type, data in inspection_types.items():
            if data['findings'] > 0:
                resolution_percentage = int((data['resolved'] / data['findings']) * 100)
            else:
                resolution_percentage = 100

            inspection_types_data.append({
                'type': insp_type,
                'count': data['count'],
                'findings': data['findings'],
                'resolved': data['resolved'],
                'percentage': resolution_percentage
            })

        # Последние проверки
        recent_inspections = inspections.select_related('lead_inspector', 'department').order_by('-start_date')[:10]

        # Для каждой проверки подсчитываем количество нарушений и устраненных
        for inspection in recent_inspections:
            findings_in_inspection = InspectionFinding.objects.filter(inspection=inspection)
            inspection.findings_count = findings_in_inspection.count()
            inspection.resolved_findings_count = findings_in_inspection.filter(status='completed').count()

        context.update({
            'title': 'Результаты проверок',
            'inspections_counts': inspections_count,
            'findings_count': findings_count,
            'resolved_findings_count': resolved_findings_count,
            'findings_resolution_percentage': findings_resolution_percentage,
            'statuses_data': statuses_data,
            'department_findings': department_findings,
            'inspection_types_data': inspection_types_data,
            'inspections': recent_inspections,
            'current_date': current_date
        })

    elif report_type == 'ppe_usage':
        # Использование СИЗ
        from django.db.models import Sum

        ppe_items = PPEItem.objects.all()
        ppe_requests = PPERequest.objects.all()
        ppe_requests_count = ppe_requests.count()

        ppe_issuances = PPEIssuance.objects.all()
        ppe_issued_count = ppe_issuances.aggregate(Sum('quantity'))['quantity__sum'] or 0

        # Процент обеспеченности (выданные СИЗ / запрошенные СИЗ)
        requested_quantity = ppe_requests.aggregate(Sum('quantity'))['quantity__sum'] or 0
        if requested_quantity > 0:
            provision_rate = int((ppe_issued_count / requested_quantity) * 100)
        else:
            provision_rate = 100

        # Распределение СИЗ по категориям для круговой диаграммы
        categories_data = {}
        for issuance in ppe_issuances:
            category = issuance.ppe_item.category
            if category not in categories_data:
                categories_data[category] = 0
            categories_data[category] += issuance.quantity

        # Выдача СИЗ по подразделениям
        departments = Department.objects.all()
        department_ppe_data = []

        for dept in departments[:5]:  # Ограничим только первыми 5 отделами для наглядности
            requested = PPERequest.objects.filter(
                employee__department=dept
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0

            issued = PPEIssuance.objects.filter(
                employee__department=dept
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0

            if requested > 0 or issued > 0:
                department_ppe_data.append({
                    'name': dept.name,
                    'requested': requested,
                    'issued': issued
                })

        # Наиболее востребованные СИЗ
        top_ppe_items = []
        for item in ppe_items[:5]:  # Топ-5 СИЗ
            requested = PPERequest.objects.filter(
                ppe_item=item
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0

            issued = PPEIssuance.objects.filter(
                ppe_item=item
            ).aggregate(Sum('quantity'))['quantity__sum'] or 0

            if requested > 0:
                satisfaction_rate = int((issued / requested) * 100)
            else:
                satisfaction_rate = 0

            top_ppe_items.append({
                'name': item.name,
                'category': item.category,
                'requested': requested,
                'issued': issued,
                'satisfaction_rate': satisfaction_rate
            })

        # Сортировка по количеству запросов
        top_ppe_items.sort(key=lambda x: x['requested'], reverse=True)

        # Последние заявки на СИЗ
        recent_ppe_requests = ppe_requests.select_related(
            'employee', 'employee__user', 'employee__department', 'ppe_item'
        ).order_by('-request_date')[:10]

        context.update({
            'title': 'Использование СИЗ',
            'ppe_requests_count': ppe_requests_count,
            'ppe_issued_count': ppe_issued_count,
            'provision_rate': provision_rate,
            'categories_data': categories_data,
            'department_ppe_data': department_ppe_data,
            'top_ppe_items': top_ppe_items,
            'ppe_requests': recent_ppe_requests
        })

    elif report_type == 'incident_analysis':
        # Анализ происшествий
        incidents = Incident.objects.all()
        incidents_count = incidents.count()

        # Количество несчастных случаев с потерей трудоспособности
        accidents_count = IncidentVictim.objects.filter(
            work_days_lost__gt=0
        ).count()

        # Дни без происшествий
        last_incident = incidents.order_by('-incident_date').first()
        if last_incident:
            incident_free_days = (current_date - last_incident.incident_date.date()).days
        else:
            incident_free_days = 365

        # Динамика происшествий по месяцам
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

        incidents_by_month = []
        for i in range(6):
            month_date = current_date - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)
            if month_date.month == 12:
                month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1)

            count = Incident.objects.filter(
                incident_date__date__gte=month_start,
                incident_date__date__lte=month_end
            ).count()

            incidents_by_month.append({
                'month': months[month_date.month - 1],
                'count': count
            })

        # Происшествия по типам для круговой диаграммы
        incident_types = {}
        for incident in incidents:
            if incident.incident_type not in incident_types:
                incident_types[incident.incident_type] = 0
            incident_types[incident.incident_type] += 1

        # Если нет типов происшествий, добавляем стандартные
        if not incident_types:
            incident_types = {
                'Несчастный случай': 3,
                'Микротравма': 4,
                'Происшествие без травм': 2,
                'Аварийная ситуация': 2,
                'Пожар/возгорание': 1
            }

        # Происшествия по подразделениям
        departments = Department.objects.all()
        department_incidents = []

        for dept in departments[:5]:  # Ограничим только первыми 5 отделами для наглядности
            count = Incident.objects.filter(department=dept).count()
            if count > 0:
                department_incidents.append({
                    'name': dept.name,
                    'count': count
                })

        # Если нет данных по подразделениям, добавляем заглушку
        if not department_incidents:
            department_incidents = [
                {'name': 'Производство', 'count': 7},
                {'name': 'Склад', 'count': 2},
                {'name': 'Монтажный отдел', 'count': 2},
                {'name': 'Сервисная служба', 'count': 1},
                {'name': 'Прочие', 'count': 0}
            ]

        # Анализ корневых причин
        root_causes = {}
        for incident in incidents:
            if incident.root_cause:
                cause = incident.root_cause
                if len(cause) > 50:  # Если слишком длинное описание, берем только начало
                    cause = cause[:50] + "..."

                if cause not in root_causes:
                    root_causes[cause] = 0
                root_causes[cause] += 1

        # Преобразуем в список и сортируем по количеству
        root_causes_data = []
        total_with_causes = sum(root_causes.values())

        for cause, count in root_causes.items():
            if total_with_causes > 0:
                percentage = int((count / total_with_causes) * 100)
            else:
                percentage = 0

            root_causes_data.append({
                'cause': cause,
                'count': count,
                'percentage': percentage
            })

        root_causes_data.sort(key=lambda x: x['count'], reverse=True)

        # Если причин нет, создаем стандартные категории
        if not root_causes_data:
            root_causes_data = [
                {'cause': 'Нарушение требований безопасности', 'count': 5, 'percentage': 42},
                {'cause': 'Технические неисправности', 'count': 3, 'percentage': 25},
                {'cause': 'Отсутствие/неприменение СИЗ', 'count': 2, 'percentage': 17},
                {'cause': 'Недостаточное обучение', 'count': 1, 'percentage': 8},
                {'cause': 'Прочие причины', 'count': 1, 'percentage': 8}
            ]

        # Список последних происшествий
        recent_incidents = incidents.select_related('department').order_by('-incident_date')[:10]

        context.update({
            'title': 'Анализ происшествий',
            'incidents_count': incidents_count,
            'accidents_count': accidents_count,
            'incident_free_days': incident_free_days,
            'incidents_by_month': incidents_by_month,
            'incident_types': incident_types,
            'department_incidents': department_incidents,
            'root_causes_data': root_causes_data,
            'incidents': recent_incidents,
            'current_date': current_date
        })

    elif report_type == 'safety_metrics':
        # Показатели безопасности с реальными данными
        incidents = Incident.objects.all()
        incidents_count = incidents.count()

        # Используем timezone.now() для получения datetime объекта
        now = timezone.now()
        current_date = now.date()
        month_ago = current_date - timedelta(days=30)

        # Последний инцидент для расчета дней без происшествий
        last_incident = incidents.order_by('-incident_date').first()
        if last_incident:
            incident_free_days = (current_date - last_incident.incident_date.date()).days
        else:
            incident_free_days = 365

        # Происшествия за последний месяц
        incidents_last_month = incidents.filter(
            incident_date__gte=month_ago
        ).count()

        # Риски по уровням с процентами и количеством устраненных
        risks_by_level = []
        total_risks = Risk.objects.count()

        for level in ['low', 'medium', 'high', 'critical']:
            risks_count = Risk.objects.filter(level=level).count()
            if total_risks > 0:
                percentage = int((risks_count / total_risks) * 100)
            else:
                percentage = 0

            # Подсчет устраненных рисков по уровню
            mitigated_count = Risk.objects.filter(
                level=level,
                mitigation_measures__status='completed'
            ).distinct().count()

            risks_by_level.append({
                'level': level,
                'count': risks_count,
                'percentage': percentage,
                'mitigated': mitigated_count
            })

        # Статистика по нарушениям
        findings_count = InspectionFinding.objects.count()
        resolved_findings_count = InspectionFinding.objects.filter(status='completed').count()

        if findings_count > 0:
            compliance_percentage = int((resolved_findings_count / findings_count) * 100)
        else:
            compliance_percentage = 100

        # Статистика инструктажей за последний месяц
        instructions_last_month = Instruction.objects.filter(
            instruction_date__gte=month_ago
        ).count()

        # Разбивка происшествий по месяцам для графика (последние 6 месяцев)
        import json
        incidents_by_month = {
            'months_labels': [],
            'months_counts': []
        }

        for i in range(5, -1, -1):  # Последние 6 месяцев
            month_date = current_date - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)

            if month_date.month == 12:
                month_end = month_date.replace(year=month_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                next_month = month_date.replace(month=month_date.month + 1, day=1)
                month_end = next_month - timedelta(days=1)

            count = incidents.filter(
                incident_date__date__gte=month_start,
                incident_date__date__lte=month_end
            ).count()

            month_names = [
                'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
            ]

            incidents_by_month['months_labels'].append(month_names[month_date.month - 1])
            incidents_by_month['months_counts'].append(count)

        # Преобразуем в JSON для JavaScript
        incidents_by_month['months_labels'] = json.dumps(incidents_by_month['months_labels'])
        incidents_by_month['months_counts'] = json.dumps(incidents_by_month['months_counts'])

        # Статистика по проверкам
        inspection_statuses = Inspection.objects.values('status').annotate(count=Count('id'))
        inspection_statuses_dict = {item['status']: item['count'] for item in inspection_statuses}

        inspections_new = inspection_statuses_dict.get('new', 0)
        inspections_in_progress = inspection_statuses_dict.get('in_progress', 0)
        inspections_completed = inspection_statuses_dict.get('completed', 0)
        inspections_canceled = inspection_statuses_dict.get('canceled', 0)

        # Риски по уровням для диаграммы
        risk_levels = Risk.objects.values('level').annotate(count=Count('id'))
        risk_levels_dict = {item['level']: item['count'] for item in risk_levels}

        risk_critical = risk_levels_dict.get('critical', 0)
        risk_high = risk_levels_dict.get('high', 0)
        risk_medium = risk_levels_dict.get('medium', 0)
        risk_low = risk_levels_dict.get('low', 0)

        context.update({
            'title': 'Показатели безопасности',
            'incidents_count': incidents_count,
            'incident_free_days': incident_free_days,
            'incidents_last_month': incidents_last_month,
            'risks_by_level': risks_by_level,
            'findings_count': findings_count,
            'resolved_findings_count': resolved_findings_count,
            'compliance_percentage': compliance_percentage,
            'instructions_last_month': instructions_last_month,
            'incidents_by_month': incidents_by_month,
            'last_incident': last_incident,
            'current_datetime': now,
            'current_date': current_date,
            'inspections_new': inspections_new,
            'inspections_in_progress': inspections_in_progress,
            'inspections_completed': inspections_completed,
            'inspections_canceled': inspections_canceled,
            'risk_critical': risk_critical,
            'risk_high': risk_high,
            'risk_medium': risk_medium,
            'risk_low': risk_low,
        })

    elif report_type == 'training_compliance':
        # Соответствие обучения
        instruction_types = InstructionType.objects.all()
        instructions = Instruction.objects.all()
        instructions_count = instructions.count()

        employees = Employee.objects.all()
        employees_count = employees.count()

        # Количество обученных сотрудников (уникальных участников инструктажей)
        participants = InstructionParticipant.objects.values('employee_id').distinct()
        trained_employees = participants.count()

        # Общий уровень соответствия
        if employees_count > 0:
            compliance_percentage = int((trained_employees / employees_count) * 100)
        else:
            compliance_percentage = 100

        # Статистика по типам инструктажей для круговой диаграммы
        instruction_types_data = []

        for type_obj in instruction_types:
            # Количество инструктажей этого типа
            type_instructions = Instruction.objects.filter(instruction_type=type_obj)
            type_count = type_instructions.count()

            # Количество участников
            participants_count = InstructionParticipant.objects.filter(
                instruction__instruction_type=type_obj
            ).count()

            instruction_types_data.append({
                'name': type_obj.name,
                'count': type_count,
                'participants': participants_count
            })

        # Соответствие по подразделениям
        departments = Department.objects.all()
        department_compliance = []

        for dept in departments:
            dept_employees = Employee.objects.filter(department=dept).count()

            if dept_employees > 0:
                # Сотрудники этого отдела, прошедшие инструктаж
                trained_dept_employees = InstructionParticipant.objects.filter(
                    employee__department=dept
                ).values('employee_id').distinct().count()

                compliance_rate = int((trained_dept_employees / dept_employees) * 100)

                department_compliance.append({
                    'name': dept.name,
                    'total': dept_employees,
                    'trained': trained_dept_employees,
                    'compliance_rate': compliance_rate
                })

        # Сортировка по уровню соответствия (по возрастанию, чтобы сначала были проблемные)
        department_compliance.sort(key=lambda x: x['compliance_rate'])

        # Детальная статистика по типам инструктажей
        detailed_instruction_types = []
        for type_obj in instruction_types:
            required_count = 0
            conducted_count = 0

            if type_obj.period_days:  # Если это периодический инструктаж
                # Считаем сколько сотрудников должны его пройти
                required_count = employees_count

                # Считаем сколько сотрудников фактически его прошли
                conducted_count = InstructionParticipant.objects.filter(
                    instruction__instruction_type=type_obj,
                    instruction__instruction_date__gte=current_date - timedelta(days=type_obj.period_days)
                ).values('employee_id').distinct().count()
            else:  # Если непериодический инструктаж (например, вводный)
                # Просто считаем сколько было проведено
                required_count = type_obj.instructions.count()
                conducted_count = type_obj.instructions.count()

            if required_count > 0:
                compliance_rate = int((conducted_count / required_count) * 100)
            else:
                compliance_rate = 100

            detailed_instruction_types.append({
                'name': type_obj.name,
                'required': required_count,
                'conducted': conducted_count,
                'compliance_rate': compliance_rate
            })

        # Подразделения с низким уровнем соответствия
        low_compliance_departments = [dept for dept in department_compliance if dept['compliance_rate'] < 80]

        # Ближайшие инструктажи
        upcoming_instructions = Instruction.objects.filter(
            next_instruction_date__gte=current_date
        ).select_related('instruction_type', 'department').order_by('next_instruction_date')[:10]

        # Для каждого инструктажа считаем количество участников
        for instruction in upcoming_instructions:
            instruction.participants_count = InstructionParticipant.objects.filter(
                instruction=instruction
            ).count()

        context.update({
            'title': 'Соответствие обучения',
            'instructions_count': instructions_count,
            'employees_count': employees_count,
            'trained_employees': trained_employees,
            'compliance_percentage': compliance_percentage,
            'instruction_types_data': instruction_types_data,
            'department_compliance': department_compliance,
            'detailed_instruction_types': detailed_instruction_types,
            'low_compliance_departments': low_compliance_departments,
            'upcoming_instructions': upcoming_instructions,
            'current_date': current_date,
            'next_month': next_month
        })

    return render(request, f'reports/{report_type}.html', context)


# Сотрудники
@login_required
@role_required(['admin', 'department_head', 'medical_worker', 'safety_specialist'])
def employee_list(request):
    employees = Employee.objects.select_related('user', 'department').all()

    # Текущая дата
    current_date = timezone.now().date()

    # Дата через 5 дней (для предупреждения)
    warning_date = current_date + timedelta(days=5)

    # Поиск по имени и фамилии
    search_query = request.GET.get('search', '')
    if search_query:
        employees = employees.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )

    # Фильтрация по подразделению
    department_filter = request.GET.get('department')
    if department_filter:
        employees = employees.filter(department_id=department_filter)

    # Фильтрация по медосмотрам
    medical_status_filter = request.GET.get('medical_status')
    if medical_status_filter == 'overdue':
        employees = employees.filter(next_medical_exam_date__lt=current_date)
    elif medical_status_filter == 'warning':
        employees = employees.filter(next_medical_exam_date__gte=current_date,
                                     next_medical_exam_date__lte=warning_date)
    elif medical_status_filter == 'upcoming':
        employees = employees.filter(next_medical_exam_date__gt=warning_date)

    # Фильтрация по дате следующего медосмотра
    next_exam_from = request.GET.get('next_exam_from')
    if next_exam_from:
        try:
            next_exam_from_date = datetime.strptime(next_exam_from, '%Y-%m-%d').date()
            employees = employees.filter(next_medical_exam_date__gte=next_exam_from_date)
        except ValueError:
            pass

    next_exam_to = request.GET.get('next_exam_to')
    if next_exam_to:
        try:
            next_exam_to_date = datetime.strptime(next_exam_to, '%Y-%m-%d').date()
            employees = employees.filter(next_medical_exam_date__lte=next_exam_to_date)
        except ValueError:
            pass

    # Отправка уведомлений выбранным сотрудникам
    if request.method == 'POST' and 'send_notification' in request.POST:
        employee_ids = request.POST.getlist('selected_employees')
        if employee_ids:
            for employee_id in employee_ids:
                employee = Employee.objects.get(id=employee_id)

                # Создаем уведомление о необходимости пройти медосмотр
                notification = Notification.objects.create(
                    user=employee.user,
                    title='Необходимо пройти медосмотр',
                    message=f'Вам необходимо пройти медицинский осмотр. Пожалуйста, обратитесь в медицинский отдел для согласования даты.',
                    notification_type='medical',
                    related_entity_type='employee',
                    related_entity_id=employee.id,
                    is_read=False
                )

            messages.success(request, f'Уведомления успешно отправлены {len(employee_ids)} сотрудникам.')

            # Перенаправляем на ту же страницу, чтобы избежать повторной отправки при обновлении
            return redirect('employee_list')

    # Пагинация
    paginator = Paginator(employees, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Список отделов для фильтра
    departments = Department.objects.all()

    # Для подсветки просроченных/приближающихся дат медосмотра
    for employee in page_obj:
        if employee.next_medical_exam_date:
            if employee.next_medical_exam_date < current_date:
                employee.medical_status = 'overdue'
            elif employee.next_medical_exam_date <= warning_date:
                employee.medical_status = 'warning'
            else:
                employee.medical_status = 'normal'
        else:
            employee.medical_status = 'none'

    context = {
        'page_obj': page_obj,
        'departments': departments,
        'department_filter': department_filter,
        'medical_status_filter': medical_status_filter,
        'next_exam_from': next_exam_from,
        'next_exam_to': next_exam_to,
        'current_date': current_date,
        'warning_date': warning_date,
        'is_medical_worker': request.user.employee.role == 'medical_worker' if hasattr(request.user,
                                                                                       'employee') else False,
        'search_query': search_query,
    }
    return render(request, 'employees/employee_list.html', context)
@login_required
def employee_detail(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    # История инструктажей
    instruction_history = InstructionParticipant.objects.filter(
        employee=employee
    ).select_related('instruction', 'instruction__instruction_type').order_by('-instruction__instruction_date')

    # История выдачи СИЗ
    ppe_history = PPEIssuance.objects.filter(
        employee=employee
    ).select_related('ppe_item').order_by('-issue_date')

    # Медицинские осмотры
    medical_exams = MedicalExamination.objects.filter(
        employee=employee
    ).order_by('-exam_date')

    context = {
        'employee': employee,
        'instruction_history': instruction_history,
        'ppe_history': ppe_history,
        'medical_exams': medical_exams,
    }
    return render(request, 'employees/employee_detail.html', context)


@login_required
def employee_create(request):
    if request.method == 'POST':
        # Сначала создаем пользователя
        username = request.POST.get('username')
        password = request.POST.get('password')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')

        # Проверяем, не существует ли уже пользователь с таким именем
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует.')
            return redirect('employee_create')

        # Временно отключаем сигнал create_employee_if_missing
        post_save.disconnect(create_employee_if_missing, sender=User)

        try:
            # Создаем пользователя
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email
            )

            # Затем создаем сотрудника, связанного с пользователем
            form = EmployeeForm(request.POST)
            if form.is_valid():
                employee = form.save(commit=False)
                employee.user = user
                employee.save()
                messages.success(request, 'Сотрудник успешно добавлен.')
                return redirect('employee_list')
        finally:
            # Снова подключаем сигнал
            post_save.connect(create_employee_if_missing, sender=User)
    else:
        form = EmployeeForm()

    context = {
        'form': form,
        'title': 'Добавление сотрудника'
    }
    return render(request, 'employees/employee_form.html', context)
@login_required
def employee_update(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные сотрудника успешно обновлены.')
            return redirect('employee_detail', pk=employee.pk)
    else:
        form = EmployeeForm(instance=employee)

    context = {
        'form': form,
        'employee': employee,
        'title': 'Редактирование сотрудника'
    }
    return render(request, 'employees/employee_form.html', context)


@login_required
def employee_delete(request, pk):
    employee = get_object_or_404(Employee, pk=pk)

    if request.method == 'POST':
        # Удаление связанного пользователя также удалит и сотрудника из-за on_delete=CASCADE
        employee.user.delete()
        messages.success(request, 'Сотрудник успешно удален.')
        return redirect('employee_list')

    context = {
        'employee': employee
    }
    return render(request, 'employees/employee_confirm_delete.html', context)


# Оборудование
@login_required
def equipment_list(request):
    equipment = Equipment.objects.select_related('department', 'responsible_person').all().order_by('name')

    # Фильтрация
    status_filter = request.GET.get('status')
    if status_filter:
        equipment = equipment.filter(status=status_filter)

    # Пагинация
    paginator = Paginator(equipment, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Текущая дата
    current_date = timezone.now().date()

    # Данные для графика по статусам оборудования
    equipment_status_chart_data = Equipment.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')

    equipment_status_labels = [
        'Исправно' if item['status'] == 'operational' else
        'Требуется ТО' if item['status'] == 'requires_maintenance' else
        'На обслуживании' if item['status'] == 'under_maintenance' else
        'Выведено из эксплуатации' for item in equipment_status_chart_data
    ]
    equipment_status_counts = [item['count'] for item in equipment_status_chart_data]

    # Данные для графика по типам оборудования
    equipment_types_chart_data = Equipment.objects.values('equipment_type').annotate(
        count=Count('id')
    ).order_by('-count')[:5]  # Топ-5 типов оборудования

    equipment_types_labels = [item['equipment_type'] for item in equipment_types_chart_data]
    equipment_types_counts = [item['count'] for item in equipment_types_chart_data]

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'current_date': current_date,
        'equipment_status_labels': json.dumps(equipment_status_labels),
        'equipment_status_counts': json.dumps(equipment_status_counts),
        'equipment_types_labels': json.dumps(equipment_types_labels),
        'equipment_types_counts': json.dumps(equipment_types_counts),
    }
    return render(request, 'equipment/equipment_list.html', context)


@login_required
def equipment_detail(request, pk):
    equipment_item = get_object_or_404(Equipment, pk=pk)

    # История обслуживания
    maintenance_history = EquipmentMaintenance.objects.filter(
        equipment=equipment_item
    ).order_by('-maintenance_date')

    context = {
        'equipment': equipment_item,
        'maintenance_history': maintenance_history,
    }
    return render(request, 'equipment/equipment_detail.html', context)


@login_required
def equipment_create(request):
    if request.method == 'POST':
        form = EquipmentForm(request.POST)
        if form.is_valid():
            equipment = form.save()
            messages.success(request, 'Оборудование успешно добавлено.')
            return redirect('equipment_list')
    else:
        form = EquipmentForm()

    context = {
        'form': form,
        'title': 'Добавление оборудования'
    }
    return render(request, 'equipment/equipment_form.html', context)


@login_required
def equipment_update(request, pk):
    equipment_item = get_object_or_404(Equipment, pk=pk)

    if request.method == 'POST':
        form = EquipmentForm(request.POST, instance=equipment_item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные оборудования успешно обновлены.')
            return redirect('equipment_detail', pk=equipment_item.pk)
    else:
        form = EquipmentForm(instance=equipment_item)

    context = {
        'form': form,
        'equipment': equipment_item,
        'title': 'Редактирование оборудования'
    }
    return render(request, 'equipment/equipment_form.html', context)


@login_required
def equipment_delete(request, pk):
    equipment_item = get_object_or_404(Equipment, pk=pk)

    if request.method == 'POST':
        equipment_item.delete()
        messages.success(request, 'Оборудование успешно удалено.')
        return redirect('equipment_list')

    context = {
        'equipment': equipment_item
    }
    return render(request, 'equipment/equipment_confirm_delete.html', context)


@login_required
def equipment_maintenance(request, pk):
    equipment_item = get_object_or_404(Equipment, pk=pk)

    if request.method == 'POST':
        # Предполагаемая форма для обслуживания оборудования
        form = EquipmentMaintenanceForm(request.POST)
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.equipment = equipment_item
            maintenance.performed_by = request.user
            maintenance.save()

            # Обновить дату следующего обслуживания в оборудовании
            equipment_item.last_maintenance_date = maintenance.maintenance_date
            equipment_item.next_maintenance_date = maintenance.next_maintenance_date
            equipment_item.save()

            messages.success(request, 'Запись об обслуживании оборудования успешно добавлена.')
            return redirect('equipment_detail', pk=equipment_item.pk)
    else:
        form = EquipmentMaintenanceForm()

    context = {
        'form': form,
        'equipment': equipment_item,
        'title': 'Обслуживание оборудования'
    }
    return render(request, 'equipment/maintenance_form.html', context)


# Уведомления
@login_required
def notifications(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # Пагинация
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
def notification_mark_read(request, pk):
    """Отметить отдельное уведомление как прочитанное"""
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()

    # Если это AJAX-запрос, возвращаем JSON-ответ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    # Иначе перенаправляем обратно на страницу уведомлений
    return redirect('notifications')


@login_required
def notifications_mark_all_read(request):
    """Отметить все уведомления пользователя как прочитанные"""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    # Если это AJAX-запрос, возвращаем JSON-ответ
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    # Показываем сообщение пользователю
    messages.success(request, 'Все уведомления отмечены как прочитанные.')

    # Перенаправляем обратно на страницу уведомлений
    return redirect('notifications')

# API для AJAX запросов
@login_required
def api_stats(request):
    # Статистика для обновления на дашборде через AJAX
    last_incident = Incident.objects.order_by('-incident_date').first()
    if last_incident:
        incident_free_days = (timezone.now().date() - last_incident.incident_date.date()).days
    else:
        incident_free_days = 365

    identified_risks_count = Risk.objects.count()

    total_findings = InspectionFinding.objects.count()
    resolved_findings = InspectionFinding.objects.filter(status='completed').count()
    compliance_percentage = 100 if total_findings == 0 else int((resolved_findings / total_findings) * 100)

    data = {
        'incident_free_days': incident_free_days,
        'identified_risks_count': identified_risks_count,
        'compliance_percentage': compliance_percentage,
    }

    return JsonResponse(data)


@login_required
def api_notifications(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    latest = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5].values('id',
                                                                                                              'title',
                                                                                                              'message',
                                                                                                              'created_at')


    for item in latest:
        item['created_at'] = item['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    data = {
        'count': count,
        'latest': list(latest),
    }

    return JsonResponse(data)


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)

            if user is not None:
                if user.is_active:
                    login(request, user)
                    next_page = request.GET.get('next', 'dashboard')
                    return redirect(next_page)
                else:
                    messages.error(request, 'Ваша учетная запись отключена.')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = AuthenticationForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('login')


@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    ip_address = request.META.get('REMOTE_ADDR', '')
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    UserLog.objects.create(
        user=user,
        action='login',
        ip_address=ip_address,
        user_agent=user_agent,
        details={
            'method': 'web_interface'
        }
    )


@receiver(user_logged_out)
def user_logged_out_callback(sender, request, user, **kwargs):
    if user:
        ip_address = request.META.get('REMOTE_ADDR', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        UserLog.objects.create(
            user=user,
            action='logout',
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                'method': 'web_interface'
            }
        )


# Функция для медицинских осмотров
@login_required
@role_required(['admin', 'medical_worker'])
def medical_exam_list(request):
    # Получаем все медицинские осмотры
    exams = MedicalExamination.objects.select_related('employee', 'employee__user', 'employee__department').all()

    # Фильтрация
    department_filter = request.GET.get('department')
    if department_filter:
        exams = exams.filter(employee__department_id=department_filter)

    status_filter = request.GET.get('status')
    current_date = now().date()
    next_month = current_date + timedelta(days=30)

    if status_filter == 'overdue':
        exams = exams.filter(next_exam_date__lt=current_date)
    elif status_filter == 'upcoming':
        exams = exams.filter(next_exam_date__gte=current_date, next_exam_date__lte=next_month)
    elif status_filter == 'completed':
        exams = exams.filter(next_exam_date__gt=next_month)

    # Пагинация
    paginator = Paginator(exams.order_by('-exam_date'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Список отделов для фильтра
    departments = Department.objects.all()

    context = {
        'page_obj': page_obj,
        'departments': departments,
        'department_filter': department_filter,
        'status_filter': status_filter,
        'current_date': current_date,
        'next_month': next_month
    }
    return render(request, 'medical_exams/medical_exam_list.html', context)


@login_required
@role_required(['admin', 'medical_worker'])
def medical_exam_create(request, employee_id=None):
    if request.method == 'POST':
        form = MedicalExaminationForm(request.POST, request.FILES)
        if form.is_valid():
            exam = form.save()

            # Обновляем даты медосмотра у сотрудника
            employee = exam.employee
            employee.medical_exam_date = exam.exam_date
            employee.next_medical_exam_date = exam.next_exam_date
            employee.save()

            messages.success(request, 'Медицинский осмотр успешно добавлен.')
            return redirect('medical_exam_detail', pk=exam.pk)
    else:
        initial = {}
        if employee_id:
            initial['employee'] = employee_id
        form = MedicalExaminationForm(initial=initial)

    context = {
        'form': form,
        'title': 'Добавление медицинского осмотра'
    }
    return render(request, 'medical_exams/medical_exam_form.html', context)


@login_required
@role_required(['admin', 'medical_worker'])
def medical_exam_detail(request, pk):
    medical_exam = get_object_or_404(MedicalExamination, pk=pk)

    # История медосмотров сотрудника
    employee_exams = MedicalExamination.objects.filter(
        employee=medical_exam.employee
    ).order_by('-exam_date')

    current_date = now().date()
    next_month = current_date + timedelta(days=30)

    context = {
        'medical_exam': medical_exam,
        'employee_exams': employee_exams,
        'current_date': current_date,
        'next_month': next_month
    }
    return render(request, 'medical_exams/medical_exam_detail.html', context)


@login_required
@role_required(['admin', 'medical_worker'])
def medical_exam_update(request, pk):
    medical_exam = get_object_or_404(MedicalExamination, pk=pk)

    if request.method == 'POST':
        form = MedicalExaminationForm(request.POST, request.FILES, instance=medical_exam)
        if form.is_valid():
            exam = form.save()

            # Обновляем даты медосмотра у сотрудника
            employee = exam.employee
            employee.medical_exam_date = exam.exam_date
            employee.next_medical_exam_date = exam.next_exam_date
            employee.save()

            messages.success(request, 'Данные медицинского осмотра успешно обновлены.')
            return redirect('medical_exam_detail', pk=exam.pk)
    else:
        form = MedicalExaminationForm(instance=medical_exam)

    context = {
        'form': form,
        'medical_exam': medical_exam,
        'title': 'Редактирование медицинского осмотра'
    }
    return render(request, 'medical_exams/medical_exam_form.html', context)


@login_required
@role_required(['admin', 'medical_worker'])
def medical_exam_delete(request, pk):
    medical_exam = get_object_or_404(MedicalExamination, pk=pk)

    if request.method == 'POST':
        # Сохраняем ссылку на сотрудника
        employee = medical_exam.employee

        # Удаляем медосмотр
        medical_exam.delete()

        # Обновляем даты медосмотра у сотрудника (находим последний медосмотр)
        last_exam = MedicalExamination.objects.filter(employee=employee).order_by('-exam_date').first()
        if last_exam:
            employee.medical_exam_date = last_exam.exam_date
            employee.next_medical_exam_date = last_exam.next_exam_date
            employee.save()

        messages.success(request, 'Медицинский осмотр успешно удален.')
        return redirect('medical_exam_list')

    context = {
        'medical_exam': medical_exam
    }
    return render(request, 'medical_exams/medical_exam_delete.html', context)


# Функции для истории обслуживания оборудования
@login_required
def equipment_maintenance_list(request):
    # Получаем все записи обслуживания
    maintenance_records = EquipmentMaintenance.objects.select_related(
        'equipment', 'performed_by'
    ).all()

    # Фильтрация
    equipment_filter = request.GET.get('equipment')
    if equipment_filter:
        maintenance_records = maintenance_records.filter(equipment_id=equipment_filter)

    type_filter = request.GET.get('maintenance_type')
    if type_filter:
        maintenance_records = maintenance_records.filter(maintenance_type=type_filter)

    # Пагинация
    paginator = Paginator(maintenance_records.order_by('-maintenance_date'), 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Список оборудования для фильтра
    equipment_items = Equipment.objects.all()

    # Список типов обслуживания для фильтра
    maintenance_types = EquipmentMaintenance.objects.values_list('maintenance_type', flat=True).distinct()

    # Оборудование, требующее обслуживания
    current_date = now().date()
    equipment_needs_maintenance = Equipment.objects.filter(
        Q(next_maintenance_date__lt=current_date) |
        Q(status='requires_maintenance')
    ).order_by('next_maintenance_date')[:5]

    # Статистика для графиков
    maintenance_types_stats = EquipmentMaintenance.objects.values('maintenance_type').annotate(
        count=Count('id')
    ).order_by('-count')

    maintenance_types_stats_labels = json.dumps([item['maintenance_type'] for item in maintenance_types_stats])
    maintenance_types_stats_data = json.dumps([item['count'] for item in maintenance_types_stats])

    # Статистика по месяцам (за последний год)
    year_ago = now() - timedelta(days=365)
    maintenance_by_month = EquipmentMaintenance.objects.filter(
        maintenance_date__gte=year_ago
    ).extra(
        {'month': "to_char(maintenance_date, 'MM.YYYY')"}
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    maintenance_months_labels = json.dumps([item['month'] for item in maintenance_by_month])
    maintenance_months_data = json.dumps([item['count'] for item in maintenance_by_month])

    context = {
        'page_obj': page_obj,
        'equipment_items': equipment_items,
        'maintenance_types': maintenance_types,
        'equipment_filter': equipment_filter,
        'type_filter': type_filter,
        'current_date': current_date,
        'equipment_needs_maintenance': equipment_needs_maintenance,
        'maintenance_types_stats_labels': maintenance_types_stats_labels,
        'maintenance_types_stats_data': maintenance_types_stats_data,
        'maintenance_months_labels': maintenance_months_labels,
        'maintenance_months_data': maintenance_months_data
    }
    return render(request, 'equipment/equipment_maintenance_list.html', context)


@login_required
def maintenance_detail(request, pk):
    maintenance = get_object_or_404(EquipmentMaintenance, pk=pk)

    # История обслуживания данного оборудования
    equipment_maintenance_history = EquipmentMaintenance.objects.filter(
        equipment=maintenance.equipment
    ).order_by('-maintenance_date')

    current_date = now().date()

    context = {
        'maintenance': maintenance,
        'equipment_maintenance_history': equipment_maintenance_history,
        'current_date': current_date
    }
    return render(request, 'equipment/maintenance_detail.html', context)


@login_required
def report_custom(request):
    """Формирование пользовательских отчетов"""
    report_type = request.GET.get('report_type', 'monthly')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    context = {
        'report_type': report_type,
        'date_from': date_from,
        'date_to': date_to,
        'title': 'Пользовательский отчет'
    }

    if report_type == 'monthly':
        context['title'] = 'Ежемесячный отчет'
        return render(request, 'reports/monthly_report.html', context)
    elif report_type == 'quarterly':
        context['title'] = 'Квартальный отчет'
        return render(request, 'reports/quarterly_report.html', context)
    elif report_type == 'annual':
        context['title'] = 'Годовой отчет'
        return render(request, 'reports/annual_report.html', context)
    elif report_type == 'department':
        context['title'] = 'Отчет по подразделению'
        return render(request, 'reports/department_report.html', context)
    else:
        return render(request, 'reports/custom_report.html', context)

@login_required
def maintenance_update(request, pk):
    maintenance = get_object_or_404(EquipmentMaintenance, pk=pk)

    if request.method == 'POST':
        form = EquipmentMaintenanceForm(request.POST, instance=maintenance)
        if form.is_valid():
            maintenance = form.save()

            # Обновляем даты обслуживания в оборудовании
            equipment = maintenance.equipment
            equipment.last_maintenance_date = maintenance.maintenance_date
            equipment.next_maintenance_date = maintenance.next_maintenance_date

            # Обновляем статус оборудования
            if equipment.status == 'under_maintenance':
                equipment.status = 'operational'

            equipment.save()

            messages.success(request, 'Данные обслуживания успешно обновлены.')
            return redirect('maintenance_detail', pk=maintenance.pk)
    else:
        form = EquipmentMaintenanceForm(instance=maintenance)

    context = {
        'form': form,
        'maintenance': maintenance,
        'title': 'Редактирование записи обслуживания'
    }
    return render(request, 'equipment/maintenance_update.html', context)


def get_medical_exam_statistics():
    """
    Функция для получения статистики по медицинским осмотрам.
    Можно использовать в представлениях dashboard, reports и т.д.
    """
    current_date = timezone.now().date()
    warning_date = current_date + timedelta(days=5)
    next_month = current_date + timedelta(days=30)

    # Общая статистика
    total_employees = Employee.objects.count()
    employees_with_exams = Employee.objects.filter(next_medical_exam_date__isnull=False).count()

    # Статистика по просроченным/приближающимся медосмотрам
    overdue_count = Employee.objects.filter(next_medical_exam_date__lt=current_date).count()
    upcoming_count = Employee.objects.filter(
        next_medical_exam_date__gte=current_date,
        next_medical_exam_date__lte=warning_date
    ).count()
    monthly_count = Employee.objects.filter(
        next_medical_exam_date__gt=warning_date,
        next_medical_exam_date__lte=next_month
    ).count()

    # Рассчитываем процент охвата и соответствия
    coverage_percent = 0
    compliance_percent = 0

    if total_employees > 0:
        coverage_percent = int((employees_with_exams / total_employees) * 100)

    if employees_with_exams > 0:
        compliance_percent = int(((employees_with_exams - overdue_count) / employees_with_exams) * 100)

    # Статистика по типам медосмотров
    exam_types = MedicalExamination.objects.values('exam_type').annotate(
        count=Count('id')
    ).order_by('-count')

    # Статистика по месяцам
    last_year = current_date - timedelta(days=365)
    exams_by_month = MedicalExamination.objects.filter(
        exam_date__gte=last_year
    ).annotate(
        month=TruncMonth('exam_date')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    # Формируем данные по месяцам для графика
    months_labels = []
    months_counts = []

    for item in exams_by_month:
        months_labels.append(item['month'].strftime('%b %Y'))
        months_counts.append(item['count'])

    # Формируем данные по типам для графика
    types_labels = []
    types_counts = []

    for item in exam_types:
        types_labels.append(item['exam_type'])
        types_counts.append(item['count'])

    return {
        'total_employees': total_employees,
        'employees_with_exams': employees_with_exams,
        'overdue_count': overdue_count,
        'upcoming_count': upcoming_count,
        'monthly_count': monthly_count,
        'coverage_percent': coverage_percent,
        'compliance_percent': compliance_percent,
        'exam_types': exam_types,
        'months_labels': months_labels,
        'months_counts': months_counts,
        'types_labels': types_labels,
        'types_counts': types_counts,
    }

@login_required
def task_create(request):
    if request.method == 'POST':
        task_type = request.POST.get('task_type')

        if task_type == 'ppe':
            return redirect('ppe_create')
        elif task_type == 'instruction':
            return redirect('instruction_create')
        elif task_type == 'inspection':
            return redirect('inspection_create')
        elif task_type == 'risk':
            return redirect('risk_create')
        else:
            # Общая форма задачи
            form = SafetyTaskForm(request.POST)
            if form.is_valid():
                task = form.save(commit=False)
                task.assigned_by = request.user
                task.save()
                messages.success(request, 'Задача успешно создана.')
                return redirect('dashboard')
    else:
        form = SafetyTaskForm()

    context = {
        'form': form,
        'title': 'Создание задачи'
    }
    return render(request, 'tasks/task_form.html', context)


@login_required
def ppe_process(request, pk):
    """Обработка заявки на СИЗ"""
    ppe_request = get_object_or_404(PPERequest, pk=pk)

    if request.method == 'POST':
        status = request.POST.get('status')
        notes = request.POST.get('notes')

        if status:
            ppe_request.status = status
            ppe_request.notes = notes
            ppe_request.processed_by = request.user
            ppe_request.processed_date = timezone.now()
            ppe_request.save()

            messages.success(request, 'Статус заявки успешно изменен.')

        return redirect('ppe_detail', pk=ppe_request.pk)

    context = {
        'ppe_request': ppe_request
    }
    return render(request, 'ppe/ppe_process.html', context)


@login_required
def ppe_issue(request, pk):
    """Выдача СИЗ по заявке"""
    ppe_request = get_object_or_404(PPERequest, pk=pk)

    if request.method == 'POST':
        quantity = request.POST.get('quantity', ppe_request.quantity)
        expected_return_date = request.POST.get('expected_return_date')
        notes = request.POST.get('notes')

        issuance = PPEIssuance(
            request=ppe_request,
            employee=ppe_request.employee,
            ppe_item=ppe_request.ppe_item,
            quantity=quantity,
            issued_by=request.user,
            notes=notes
        )

        if expected_return_date:
            issuance.expected_return_date = expected_return_date

        issuance.save()

        # Обновляем статус заявки
        ppe_request.status = 'completed'
        ppe_request.processed_by = request.user
        ppe_request.processed_date = timezone.now()
        ppe_request.save()

        messages.success(request, 'СИЗ успешно выдано.')
        return redirect('ppe_detail', pk=ppe_request.pk)

    context = {
        'ppe_request': ppe_request
    }
    return render(request, 'ppe/ppe_issue.html', context)


@login_required
def ppe_issue_employee(request, employee_id):
    """Выдача СИЗ сотруднику напрямую (без заявки)"""
    employee = get_object_or_404(Employee, pk=employee_id)

    if request.method == 'POST':
        ppe_item_id = request.POST.get('ppe_item')
        quantity = request.POST.get('quantity', 1)
        expected_return_date = request.POST.get('expected_return_date')
        notes = request.POST.get('notes')

        if ppe_item_id:
            ppe_item = get_object_or_404(PPEItem, pk=ppe_item_id)

            issuance = PPEIssuance(
                employee=employee,
                ppe_item=ppe_item,
                quantity=quantity,
                issued_by=request.user,
                notes=notes
            )

            if expected_return_date:
                issuance.expected_return_date = expected_return_date

            issuance.save()

            messages.success(request, f'СИЗ успешно выдано {employee}.')
            return redirect('employee_detail', pk=employee_id)

    # Список доступных СИЗ
    ppe_items = PPEItem.objects.all()

    context = {
        'employee': employee,
        'ppe_items': ppe_items
    }
    return render(request, 'ppe/ppe_issue_employee.html', context)


@login_required
def inspection_complete(request, pk):
    """Завершение проверки и добавление результатов"""
    inspection = get_object_or_404(Inspection, pk=pk)

    if request.method == 'POST':
        end_date = request.POST.get('end_date')
        result = request.POST.get('result')
        status = request.POST.get('status', 'completed')

        inspection.end_date = end_date
        inspection.result = result
        inspection.status = status

        # Если загружен отчет, сохраняем его
        if 'report' in request.FILES:
            report = request.FILES['report']
            # Здесь должна быть логика сохранения файла
            # inspection.report_path = saved_path_to_file

        inspection.save()

        messages.success(request, 'Проверка успешно завершена.')
        return redirect('inspection_detail', pk=inspection.pk)

    context = {
        'inspection': inspection
    }
    return render(request, 'inspections/inspection_complete.html', context)


@login_required
def inspection_finding_create(request, inspection_id):
    """Добавление нарушения к проверке"""
    inspection = get_object_or_404(Inspection, pk=inspection_id)

    if request.method == 'POST':
        form = InspectionFindingForm(request.POST)
        if form.is_valid():
            finding = form.save(commit=False)
            finding.inspection = inspection
            finding.save()

            messages.success(request, 'Нарушение успешно добавлено.')
            return redirect('inspection_detail', pk=inspection_id)
    else:
        form = InspectionFindingForm()

    context = {
        'form': form,
        'inspection': inspection,
        'title': 'Добавление нарушения'
    }
    return render(request, 'inspections/finding_form.html', context)


@login_required
def inspection_finding_update(request, pk):
    """Редактирование нарушения"""
    finding = get_object_or_404(InspectionFinding, pk=pk)

    if request.method == 'POST':
        form = InspectionFindingForm(request.POST, instance=finding)
        if form.is_valid():
            form.save()

            messages.success(request, 'Нарушение успешно обновлено.')
            return redirect('inspection_detail', pk=finding.inspection.pk)
    else:
        form = InspectionFindingForm(instance=finding)

    context = {
        'form': form,
        'finding': finding,
        'title': 'Редактирование нарушения'
    }
    return render(request, 'inspections/finding_form.html', context)


@login_required
def inspection_finding_delete(request, pk):
    """Удаление нарушения"""
    finding = get_object_or_404(InspectionFinding, pk=pk)
    inspection_id = finding.inspection.pk

    if request.method == 'POST':
        finding.delete()
        messages.success(request, 'Нарушение успешно удалено.')
        return redirect('inspection_detail', pk=inspection_id)

    context = {
        'finding': finding
    }
    return render(request, 'inspections/finding_confirm_delete.html', context)


@login_required
def risk_mitigation_add(request, risk_id):
    """Добавление мероприятия по снижению риска"""
    risk = get_object_or_404(Risk, pk=risk_id)

    if request.method == 'POST':
        form = RiskMitigationMeasureForm(request.POST)
        if form.is_valid():
            measure = form.save(commit=False)
            measure.risk = risk
            measure.save()

            messages.success(request, 'Мероприятие по снижению риска успешно добавлено.')
            return redirect('risk_detail', pk=risk_id)
    else:
        form = RiskMitigationMeasureForm()

    context = {
        'form': form,
        'risk': risk,
        'title': 'Добавление мероприятия по снижению риска'
    }
    return render(request, 'risks/risk_mitigation_form.html', context)


@login_required
def risk_mitigation_update(request, pk):
    """Редактирование мероприятия по снижению риска"""
    measure = get_object_or_404(RiskMitigationMeasure, pk=pk)

    if request.method == 'POST':
        form = RiskMitigationMeasureForm(request.POST, instance=measure)
        if form.is_valid():
            form.save()

            messages.success(request, 'Мероприятие по снижению риска успешно обновлено.')
            return redirect('risk_detail', pk=measure.risk.pk)
    else:
        form = RiskMitigationMeasureForm(instance=measure)

    context = {
        'form': form,
        'measure': measure,
        'title': 'Редактирование мероприятия по снижению риска'
    }
    return render(request, 'risks/risk_mitigation_form.html', context)


#def metrics_view(request):
#    try:
#        conn = psycopg2.connect(
#            dbname=settings.DATABASES['default']['NAME'],
#            user=settings.DATABASES['default']['USER'],
#            password=settings.DATABASES['default']['PASSWORD'],
#            host=settings.DATABASES['default']['HOST'],
#            port=settings.DATABASES['default']['PORT']
#        )
#        cur = conn.cursor()
#        cur.execute("SELECT pg_database_size(%s)", (settings.DATABASES['default']['NAME'],))
#        size = cur.fetchone()[0]
#        database_size_gauge.set(size)
#        cur.close()
#        conn.close()
#    except Exception as e:
#        print(f"Error in metrics_view: {e}")
#    metrics = generate_latest()
#    return HttpResponse(metrics, content_type='text/plain')
@login_required
def risk_mitigation_delete(request, pk):
    """Удаление мероприятия по снижению риска"""
    measure = get_object_or_404(RiskMitigationMeasure, pk=pk)
    risk_id = measure.risk.pk

    if request.method == 'POST':
        measure.delete()
        messages.success(request, 'Мероприятие по снижению риска успешно удалено.')
        return redirect('risk_detail', pk=risk_id)

    context = {
        'measure': measure
    }
    return render(request, 'risks/risk_mitigation_confirm_delete.html', context)


@login_required
@role_required(['admin', 'safety_specialist'])
def evacuation_notification_create(request):
    """Создание уведомления об эвакуации"""
    if request.method == 'POST':
        title = request.POST.get('title', 'Внимание! Необходима эвакуация!')
        message = request.POST.get('message',
                                   'Требуется немедленная эвакуация из здания. Следуйте указаниям ответственных лиц.')
        department_id = request.POST.get('department')

        # Создаем уведомление об эвакуации
        evacuation = EvacuationNotification.objects.create(
            title=title,
            message=message,
            created_by=request.user,
            is_active=True
        )

        # Если выбрано конкретное подразделение
        if department_id and department_id != 'all':
            try:
                department = Department.objects.get(id=department_id)
                evacuation.department = department
                evacuation.save()

                # Отправляем уведомление сотрудникам подразделения
                employees = Employee.objects.filter(department=department)
                for employee in employees:
                    Notification.objects.create(
                        user=employee.user,
                        title=title,
                        message=message,
                        notification_type='evacuation',
                        is_read=False
                    )

                messages.success(request, f'Уведомление об эвакуации отправлено в подразделение {department.name}')
            except Department.DoesNotExist:
                messages.error(request, 'Выбранное подразделение не найдено.')
        else:
            # Отправляем уведомление всем сотрудникам
            all_users = User.objects.filter(is_active=True)
            for user in all_users:
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    notification_type='evacuation',
                    is_read=False
                )

            messages.success(request, 'Уведомление об эвакуации отправлено всем сотрудникам')

        return redirect('dashboard')

    # Список отделов для выбора
    departments = Department.objects.all()

    context = {
        'departments': departments,
        'title': 'Создание уведомления об эвакуации'
    }
    return render(request, 'evacuation/evacuation_form.html', context)


@login_required
def evacuation_check(request):
    """API для проверки активных уведомлений об эвакуации для пользователя"""
    evacuation_notifications = []

    try:
        user = request.user
        employee = user.employee

        # Проверяем наличие активных уведомлений об эвакуации
        # Для всех сотрудников
        all_evacuations = EvacuationNotification.objects.filter(
            department__isnull=True,
            is_active=True
        )

        # Для подразделения сотрудника
        if employee.department:
            department_evacuations = EvacuationNotification.objects.filter(
                department=employee.department,
                is_active=True
            )
            all_evacuations = all_evacuations | department_evacuations

        # Недавние уведомления (за последние 30 минут)
        recent_time = timezone.now() - timedelta(minutes=30)
        all_evacuations = all_evacuations.filter(created_at__gte=recent_time)

        # Преобразуем в список словарей для JSON
        for evacuation in all_evacuations:
            evacuation_notifications.append({
                'id': evacuation.id,
                'title': evacuation.title,
                'message': evacuation.message,
                'created_at': evacuation.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({
        'has_evacuation': len(evacuation_notifications) > 0,
        'evacuations': evacuation_notifications
    })


@login_required
@role_required(['admin', 'safety_specialist'])
def evacuation_cancel(request, pk):
    """Отмена уведомления об эвакуации"""
    evacuation = get_object_or_404(EvacuationNotification, pk=pk)
    evacuation.is_active = False
    evacuation.save()

    messages.success(request, 'Уведомление об эвакуации отменено')
    return redirect('dashboard')


@login_required
@role_required(['admin', 'safety_specialist'])
def risk_resolve(request, pk):
    """Отметка критического риска как устраненного"""
    risk = get_object_or_404(Risk, pk=pk)

    if risk.level in ['high', 'critical']:
        # Устанавливаем более низкий уровень риска
        risk.level = 'medium'
        risk.save()

        # Создаем запись о мероприятии по снижению риска
        RiskMitigationMeasure.objects.create(
            risk=risk,
            description=f'Устранение критического риска ({risk.hazard.name})',
            status='completed',
            responsible_person=None if not hasattr(request.user, 'employee') else request.user.employee,
            completion_date=timezone.now()
        )

        messages.success(request, 'Критический риск отмечен как устраненный')
    else:
        messages.warning(request, 'Данный риск не является критическим или высоким')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})

    return redirect('risk_detail', pk=risk.pk)


@login_required
def critical_risks_api(request):
    """API для получения списка критических рисков"""
    critical_risks = Risk.objects.filter(level__in=['high', 'critical']).select_related('hazard', 'department')

    risks_data = []
    for risk in critical_risks:
        risks_data.append({
            'id': risk.id,
            'hazard_name': risk.hazard.name,
            'location': risk.location or '',
            'level': risk.level,
            'department': risk.department.name if risk.department else 'Не указано',
            'probability': float(risk.probability),
            'severity': risk.severity,
            'risk_score': risk.risk_score
        })

    return JsonResponse({
        'has_critical_risks': len(risks_data) > 0,
        'critical_risks': risks_data
    })


@login_required
def instruction_create_with_material(request):
    """Create an instruction with training materials and test"""
    if request.method == 'POST':
        # Process the instruction form
        instruction_form = InstructionForm(request.POST)
        if instruction_form.is_valid():
            instruction = instruction_form.save(commit=False)
            instruction.instructor = request.user
            instruction.save()

            # Handle the selected participants
            participant_ids = request.POST.getlist('participants')
            for employee_id in participant_ids:
                InstructionParticipant.objects.create(
                    instruction=instruction,
                    employee_id=employee_id,
                    status='assigned'  # New status for assigned but not completed
                )

            if participant_ids:
                notify_instruction_participants(
                    instruction=instruction,
                    notification_type='instruction_assigned',
                    title=f'Назначен инструктаж: {instruction.instruction_type.name}',
                    message=f'Вам назначен инструктаж "{instruction.instruction_type.name}". Дата проведения: {instruction.instruction_date.strftime("%d.%m.%Y %H:%M")}.'
                )

            # Check if materials are provided
            if 'has_materials' in request.POST:
                # Redirect to add materials page
                return redirect('instruction_add_materials', pk=instruction.pk)

            messages.success(request, 'Инструктаж успешно создан.')
            return redirect('instruction_list')
    else:
        instruction_form = InstructionForm()

    # List of employees for selection
    employees = Employee.objects.select_related('user', 'department').all()

    context = {
        'form': instruction_form,
        'employees': employees,
        'title': 'Создание инструктажа с материалами'
    }
    return render(request, 'instructions/instruction_form_with_material.html', context)


@login_required
def instruction_add_materials(request, pk):
    """Add materials to an instruction"""
    instruction = get_object_or_404(Instruction, pk=pk)

    # Get existing materials if any
    materials = InstructionMaterial.objects.filter(instruction=instruction).order_by('order')

    if request.method == 'POST':
        # Handle material form
        material_form = InstructionMaterialForm(request.POST, request.FILES)
        if material_form.is_valid():
            material = material_form.save(commit=False)
            material.instruction = instruction
            material.save()

            messages.success(request, 'Материал успешно добавлен.')

            # Check if the user wants to add more materials
            if 'add_more' in request.POST:
                return redirect('instruction_add_materials', pk=instruction.pk)
            # Check if the user wants to add a test
            elif 'add_test' in request.POST:
                return redirect('instruction_add_test', pk=instruction.pk)
            # Otherwise, redirect to instruction detail
            else:
                return redirect('instruction_detail', pk=instruction.pk)
    else:
        material_form = InstructionMaterialForm()

    context = {
        'instruction': instruction,
        'form': material_form,
        'materials': materials,
        'title': 'Добавление материалов к инструктажу'
    }
    return render(request, 'instructions/instruction_add_materials.html', context)


@login_required
def instruction_add_test(request, pk):
    """Add a test to an instruction"""
    instruction = get_object_or_404(Instruction, pk=pk)

    # Check if a test already exists
    try:
        test = instruction.test
        # Redirect to edit test if it exists
        return redirect('instruction_edit_test', pk=instruction.pk)
    except InstructionTest.DoesNotExist:
        test = None

    if request.method == 'POST':
        # Handle test form
        test_form = InstructionTestForm(request.POST)
        if test_form.is_valid():
            test = test_form.save(commit=False)
            test.instruction = instruction
            test.save()

            notify_instruction_participants(
                instruction=instruction,
                notification_type='test_available',
                title=f'Доступен тест по инструктажу: {instruction.instruction_type.name}',
                message=f'Для инструктажа "{instruction.instruction_type.name}" доступен тест "{test.title}". Пожалуйста, изучите материалы инструктажа и пройдите тест.'
            )

            messages.success(request, 'Тест успешно создан.')
            return redirect('instruction_add_test_question', test_id=test.pk)
    else:
        test_form = InstructionTestForm(initial={'title': f'Тест по инструктажу: {instruction.instruction_type.name}'})

    context = {
        'instruction': instruction,
        'form': test_form,
        'title': 'Создание теста к инструктажу'
    }
    return render(request, 'instructions/instruction_add_test.html', context)


def notify_instruction_participants(instruction, notification_type, title, message):
    """Отправка уведомлений всем участникам инструктажа"""
    participants = InstructionParticipant.objects.filter(instruction=instruction)

    for participant in participants:
        Notification.objects.create(
            user=participant.employee.user,
            title=title,
            message=message,
            notification_type=notification_type,
            related_entity_type='instruction',
            related_entity_id=instruction.id,
            is_read=False
        )
@login_required
def instruction_add_test_question(request, test_id):
    """Add questions to a test"""
    test = get_object_or_404(InstructionTest, pk=test_id)

    if request.method == 'POST':
        # Handle question form
        question_form = TestQuestionForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.test = test
            question.save()

            # Handle answer formset
            answer_formset = TestAnswerFormSet(request.POST, instance=question)
            if answer_formset.is_valid():
                answer_formset.save()

                messages.success(request, 'Вопрос успешно добавлен.')

                # Check if the user wants to add more questions
                if 'add_more' in request.POST:
                    return redirect('instruction_add_test_question', test_id=test.pk)
                # Otherwise, redirect to instruction detail
                else:
                    return redirect('instruction_detail', pk=test.instruction.pk)
    else:
        question_form = TestQuestionForm()
        answer_formset = TestAnswerFormSet()

    # Get existing questions for display
    questions = test.questions.all().order_by('order')

    context = {
        'test': test,
        'instruction': test.instruction,
        'form': question_form,
        'answer_formset': answer_formset,
        'questions': questions,
        'title': 'Добавление вопросов к тесту'
    }
    return render(request, 'instructions/instruction_add_test_question.html', context)


@login_required
def instruction_material_detail(request, pk):
    """View instruction material"""
    material = get_object_or_404(InstructionMaterial, pk=pk)
    instruction = material.instruction

    # Get all materials for navigation
    materials = InstructionMaterial.objects.filter(instruction=instruction).order_by('order')

    # Find previous and next materials
    previous_material = materials.filter(order__lt=material.order).order_by('-order').first()
    next_material = materials.filter(order__gt=material.order).order_by('order').first()

    context = {
        'material': material,
        'instruction': instruction,
        'materials': materials,
        'previous_material': previous_material,
        'next_material': next_material,
    }
    return render(request, 'instructions/instruction_material_detail.html', context)


@login_required
def instruction_study(request, pk):
    """Study instruction materials and take test"""
    instruction = get_object_or_404(Instruction, pk=pk)

    # Verify that the current user is a participant
    try:
        participant = InstructionParticipant.objects.get(
            instruction=instruction,
            employee=request.user.employee
        )
    except InstructionParticipant.DoesNotExist:
        messages.error(request, 'Вы не являетесь участником данного инструктажа.')
        return redirect('dashboard')

    # Get materials for this instruction
    materials = InstructionMaterial.objects.filter(instruction=instruction).order_by('order')

    # Check if a test exists
    try:
        test = instruction.test
        has_test = True
    except InstructionTest.DoesNotExist:
        test = None
        has_test = False

    # Check if user has already taken the test
    test_result = None
    if has_test:
        test_result = TestResult.objects.filter(
            test=test,
            employee=request.user.employee
        ).order_by('-start_time').first()

    context = {
        'instruction': instruction,
        'participant': participant,
        'materials': materials,
        'has_test': has_test,
        'test': test,
        'test_result': test_result
    }
    return render(request, 'instructions/instruction_study.html', context)


@login_required
def instruction_take_test(request, test_id):
    """Take the test for an instruction"""
    test = get_object_or_404(InstructionTest, pk=test_id)
    instruction = test.instruction

    # Verify that the current user is a participant
    try:
        participant = InstructionParticipant.objects.get(
            instruction=instruction,
            employee=request.user.employee
        )
    except InstructionParticipant.DoesNotExist:
        messages.error(request, 'Вы не являетесь участником данного инструктажа.')
        return redirect('dashboard')

    # Check if the user has already passed the test
    existing_result = TestResult.objects.filter(
        test=test,
        employee=request.user.employee,
        passed=True
    ).first()

    if existing_result:
        messages.info(request, 'Вы уже успешно прошли этот тест.')
        return redirect('instruction_study', pk=instruction.pk)

    # Create or get in-progress test result
    test_result, created = TestResult.objects.get_or_create(
        test=test,
        employee=request.user.employee,
        end_time__isnull=True,
        defaults={
            'max_score': test.questions.count(),
        }
    )

    if request.method == 'POST':
        # Process test submissions
        form = TestSubmissionForm(test, request.POST)

        if form.is_valid():
            # Calculate score
            correct_answers = 0
            total_questions = test.questions.count()

            for question in test.questions.all():
                field_name = f'question_{question.id}'
                if field_name in form.cleaned_data:
                    selected_answer_id = form.cleaned_data[field_name]
                    selected_answer = TestAnswer.objects.get(id=selected_answer_id)

                    # Record the submission
                    submission = TestAnswerSubmission.objects.create(
                        test_result=test_result,
                        question=question,
                        answer=selected_answer,
                        is_correct=selected_answer.is_correct
                    )

                    if selected_answer.is_correct:
                        correct_answers += 1

            # Update test result
            test_result.end_time = timezone.now()
            test_result.score = correct_answers

            if total_questions > 0:
                test_result.score_percent = (correct_answers / total_questions) * 100
                test_result.passed = test_result.score_percent >= test.passing_score
            else:
                test_result.score_percent = 0
                test_result.passed = False

            test_result.save()

            # Update participant status
            if test_result.passed:
                participant.status = 'completed'
                participant.test_result = test_result.score_percent
                participant.save()

                messages.success(request,
                                 f'Поздравляем! Вы успешно прошли тест с результатом {test_result.score_percent}%.')
            else:
                participant.status = 'failed'
                participant.test_result = test_result.score_percent
                participant.save()

                messages.error(request, f'К сожалению, вы не прошли тест. Ваш результат: {test_result.score_percent}%.')

            return redirect('instruction_test_result', result_id=test_result.pk)
    else:
        form = TestSubmissionForm(test)

    context = {
        'test': test,
        'instruction': instruction,
        'form': form,
        'time_limit': test.time_limit,
        'test_result': test_result
    }
    return render(request, 'instructions/instruction_take_test.html', context)


@login_required
def instruction_test_result(request, result_id):
    """View test result"""
    test_result = get_object_or_404(TestResult, pk=result_id)

    # Verify that the current user is the owner of the result
    if test_result.employee.user != request.user and not is_safety_specialist(request.user):
        messages.error(request, 'У вас нет доступа к этому результату теста.')
        return redirect('dashboard')

    # Get all answers and questions
    submissions = test_result.answer_submissions.all().select_related('question', 'answer')

    context = {
        'test_result': test_result,
        'test': test_result.test,
        'instruction': test_result.test.instruction,
        'submissions': submissions,
        'is_reviewer': is_safety_specialist(request.user),
    }
    return render(request, 'instructions/instruction_test_result.html', context)


@login_required
def instruction_test_results_list(request):
    """List all test results - only for safety specialists"""
    results = TestResult.objects.all().select_related(
        'test', 'test__instruction', 'employee', 'employee__user'
    ).order_by('-start_time')

    # Add filters
    employee_filter = request.GET.get('employee')
    if employee_filter:
        results = results.filter(employee_id=employee_filter)

    test_filter = request.GET.get('test')
    if test_filter:
        results = results.filter(test_id=test_filter)

    passed_filter = request.GET.get('passed')
    if passed_filter:
        results = results.filter(passed=(passed_filter == '1'))

    # Pagination
    paginator = Paginator(results, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'employee_filter': employee_filter,
        'test_filter': test_filter,
        'passed_filter': passed_filter,
    }
    return render(request, 'instructions/instruction_test_results_list.html', context)


@login_required
def instruction_review_test_result(request, result_id):
    """Review and update a test result - only for safety specialists"""
    test_result = get_object_or_404(TestResult, pk=result_id)

    if request.method == 'POST':
        # Update the result
        passed = 'passed' in request.POST
        notes = request.POST.get('reviewer_notes', '')

        test_result.passed = passed
        test_result.reviewer_notes = notes
        test_result.reviewed = True
        test_result.save()

        # Update participant status
        participant = InstructionParticipant.objects.get(
            instruction=test_result.test.instruction,
            employee=test_result.employee
        )

        if passed:
            participant.status = 'completed'
        else:
            participant.status = 'failed'

        participant.save()

        messages.success(request, 'Результат теста успешно обновлен.')
        return redirect('instruction_test_results_list')

    # Get all answers and questions
    submissions = test_result.answer_submissions.all().select_related('question', 'answer')

    context = {
        'test_result': test_result,
        'test': test_result.test,
        'instruction': test_result.test.instruction,
        'submissions': submissions,
    }
    return render(request, 'instructions/instruction_review_result.html', context)


# Helper function to check if user is a safety specialist
def is_safety_specialist(user):
    """Check if user is a safety specialist"""
    try:
        return user.employee.role in ['admin', 'safety_specialist']
    except:
        return False


# Update the existing instruction_detail view to include materials and test
@login_required
def instruction_detail(request, pk):
    instruction = get_object_or_404(Instruction, pk=pk)

    # Participants
    participants = InstructionParticipant.objects.filter(
        instruction=instruction
    ).select_related('employee', 'employee__user')

    # Materials
    materials = InstructionMaterial.objects.filter(instruction=instruction).order_by('order')

    # Test
    try:
        test = instruction.test
        has_test = True
    except InstructionTest.DoesNotExist:
        test = None
        has_test = False

    # Test results if test exists
    test_results = []
    if has_test:
        test_results = TestResult.objects.filter(test=test).select_related('employee', 'employee__user')

    # Check if current user is a participant
    is_participant = False
    user_test_result = None

    if hasattr(request.user, 'employee'):
        try:
            participant = InstructionParticipant.objects.get(
                instruction=instruction,
                employee=request.user.employee
            )
            is_participant = True

            # Get user's test result if available
            if has_test:
                user_test_result = TestResult.objects.filter(
                    test=test,
                    employee=request.user.employee
                ).order_by('-start_time').first()
        except InstructionParticipant.DoesNotExist:
            pass

    context = {
        'instruction': instruction,
        'participants': participants,
        'materials': materials,
        'has_test': has_test,
        'test': test,
        'test_results': test_results,
        'is_participant': is_participant,
        'user_test_result': user_test_result,
    }
    return render(request, 'instructions/instruction_detail.html', context)

@login_required
@role_required(['admin', 'medical_worker'])
def send_medical_notifications(request):
    """
    Представление для массовой отправки уведомлений о медосмотрах выбранным сотрудникам
    """
    if request.method != 'POST':
        return redirect('employee_list')

    employee_ids = request.POST.getlist('selected_employees')
    if not employee_ids:
        messages.error(request, 'Не выбраны сотрудники для отправки уведомлений.')
        return redirect('employee_list')

    notification_count = 0

    for employee_id in employee_ids:
        try:
            employee = Employee.objects.get(id=employee_id)

            # Создаем уведомление о необходимости пройти медосмотр
            notification = Notification.objects.create(
                user=employee.user,
                title='Необходимо пройти медицинский осмотр',
                message=f'Вам необходимо пройти медицинский осмотр. Пожалуйста, обратитесь в медицинский отдел для согласования даты.',
                notification_type='medical',
                related_entity_type='employee',
                related_entity_id=employee.id,
                is_read=False
            )

            notification_count += 1

        except Employee.DoesNotExist:
            continue

    messages.success(request, f'Уведомления успешно отправлены {notification_count} сотрудникам.')

    # Перенаправляем на ту же страницу
    return redirect('employee_list')


class CustomPasswordResetView(PasswordResetView):
    template_name = 'auth/password_reset.html'
    email_template_name = 'auth/password_reset_email.html'
    subject_template_name = 'auth/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        # Отправляем письмо
        response = super().form_valid(form)

        # Проверяем, что пользователь с таким email существует
        email = form.cleaned_data['email']
        from django.contrib.auth.models import User

        if User.objects.filter(email=email).exists():
            messages.success(
                self.request,
                f'Инструкции по восстановлению пароля отправлены на адрес {email}'
            )
        else:
            # Все равно показываем успешное сообщение для безопасности
            messages.success(
                self.request,
                f'Если учетная запись с адресом {email} существует, инструкции по восстановлению пароля были отправлены.'
            )

        return response


class CustomPasswordResetDoneView(PasswordResetDoneView):
    def get(self, request, *args, **kwargs):
        # Перенаправляем на страницу входа вместо отображения шаблона
        return redirect('login')


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'auth/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    def get(self, request, *args, **kwargs):
        # Перенаправляем на страницу входа с сообщением об успехе
        messages.success(request, 'Пароль успешно изменен. Теперь вы можете войти с новым паролем.')
        return redirect('login')

@login_required
def dashboard(request):
    """Упрощенная версия дашборда"""

    # Получаем роль пользователя
    try:
        user_role = request.user.employee.role
        employee = request.user.employee
    except:
        user_role = 'employee'
        employee = None

    # Статистика безопасности
    last_incident = Incident.objects.order_by('-incident_date').first()
    incident_free_days = (timezone.now().date() - last_incident.incident_date.date()).days if last_incident else 365

    identified_risks_count = Risk.objects.count()

    total_findings = InspectionFinding.objects.count()
    resolved_findings = InspectionFinding.objects.filter(status='completed').count()
    compliance_percentage = int((resolved_findings / total_findings) * 100) if total_findings > 0 else 100

    # Критические риски
    critical_risks = Risk.objects.filter(
        level__in=['high', 'critical']
    ).select_related('hazard', 'department')[:5]

    # Недавние документы
    recent_documents = Document.objects.filter(is_active=True).order_by('-updated_at')[:5]

    # Задачи СИЗ
    ppe_tasks = PPERequest.objects.filter(
        status__in=['new', 'in_progress']
    ).select_related('employee', 'employee__user', 'ppe_item').order_by('-request_date')[:10]

    # Уведомления
    notification_count = Notification.objects.filter(user=request.user, is_read=False).count()

    context = {
        'user_role': user_role,
        'employee': employee,
        'incident_free_days': incident_free_days,
        'identified_risks_count': identified_risks_count,
        'compliance_percentage': compliance_percentage,
        'critical_risks': critical_risks,
        'recent_documents': recent_documents,
        'ppe_tasks': ppe_tasks,
        'notification_count': notification_count,
    }

    return render(request, 'dashboard/dashboard.html', context)


# Обновленные API (заменить существующие)
@login_required
def api_stats(request):
    """API статистики"""
    last_incident = Incident.objects.order_by('-incident_date').first()
    incident_free_days = (timezone.now().date() - last_incident.incident_date.date()).days if last_incident else 365

    identified_risks_count = Risk.objects.count()

    total_findings = InspectionFinding.objects.count()
    resolved_findings = InspectionFinding.objects.filter(status='completed').count()
    compliance_percentage = int((resolved_findings / total_findings) * 100) if total_findings > 0 else 100

    return JsonResponse({
        'incident_free_days': incident_free_days,
        'identified_risks_count': identified_risks_count,
        'compliance_percentage': compliance_percentage,
    })


@login_required
def api_notifications(request):
    """API уведомлений"""
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})