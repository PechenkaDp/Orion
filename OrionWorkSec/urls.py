from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views
from core.admin_site import orion_admin_site
from django.contrib.auth.decorators import login_required
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

from core.views import CustomPasswordResetView, CustomPasswordResetDoneView, CustomPasswordResetConfirmView, \
    CustomPasswordResetCompleteView


def role_required(allowed_roles):

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            try:
                user_role = request.user.employee.role
            except:
                user_role = 'employee'

            if user_role not in allowed_roles:
                messages.error(request, 'У вас нет доступа к данной функции.')
                return redirect('dashboard')

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def view_only(view_func):
    """
    Декоратор, который разрешает только GET-запросы (только просмотр).
    При попытке изменения показывает сообщение об ошибке.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.method != 'GET':
            messages.error(request, 'У вас есть доступ только для просмотра данного раздела.')
            current_url = request.path
            return redirect(current_url)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


urlpatterns = [
    # Аутентификация
    path('', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('password_reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # Главная страница и поиск - доступ у всех авторизованных пользователей
    path('dashboard/', login_required(views.dashboard), name='dashboard'),
    path('search/', login_required(views.search), name='search'),

    # Мероприятия по снижению рисков
    path('risks/<int:risk_id>/mitigation/add/', login_required(views.risk_mitigation_add), name='risk_mitigation_add'),
    path('risks/mitigation/<int:pk>/update/', login_required(views.risk_mitigation_update), name='risk_mitigation_update'),
    path('risks/mitigation/<int:pk>/delete/', login_required(views.risk_mitigation_delete), name='risk_mitigation_delete'),

    # Профиль - доступ у всех авторизованных пользователей
    path('profile/', login_required(views.profile), name='profile'),

    # Настройки (только для администратора)
    path('settings/', login_required(role_required(['admin'])(views.settings)), name='settings'),

    # Задачи СИЗ
    # Просмотр списка - только определенные роли
    path('ppe/', login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.ppe_list)),
         name='ppe_list'),
    # Детали заявки - доступны всем (проверка внутри представления)
    path('ppe/<int:pk>/', login_required(views.ppe_detail), name='ppe_detail'),
    # Создание заявки - доступно всем
    path('ppe/create/', login_required(views.ppe_create), name='ppe_create'),
    # Редактирование, удаление и обработка - только определенные роли
    path('ppe/<int:pk>/update/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.ppe_update)),
         name='ppe_update'),
    path('ppe/<int:pk>/delete/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.ppe_delete)),
         name='ppe_delete'),
    path('ppe/<int:pk>/process/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.ppe_process)),
         name='ppe_process'),
    path('ppe/<int:pk>/issue/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.ppe_issue)),
         name='ppe_issue'),
    path('ppe/issue/<int:employee_id>/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.ppe_issue_employee)),
         name='ppe_issue_employee'),

    # Инструктажи
    path('instructions/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.instruction_list)),
         name='instruction_list'),
    path('instructions/<int:pk>/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.instruction_detail)),
         name='instruction_detail'),
    path('instructions/create/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.instruction_create)),
         name='instruction_create'),
    path('instructions/<int:pk>/update/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.instruction_update)),
         name='instruction_update'),
    path('instructions/<int:pk>/delete/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.instruction_delete)),
         name='instruction_delete'),

    # Документы - просмотр для всех, редактирование только для определенных ролей
    path('documents/', login_required(views.document_list), name='document_list'),
    path('documents/<int:pk>/', login_required(views.document_detail), name='document_detail'),
    path('documents/create/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.document_create)),
         name='document_create'),
    path('documents/<int:pk>/update/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.document_update)),
         name='document_update'),
    path('documents/<int:pk>/delete/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.document_delete)),
         name='document_delete'),

    # Риски - департамент только просмотр
    path('risks/', login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.risk_list)),
         name='risk_list'),
    path('risks/<int:pk>/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.risk_detail)),
         name='risk_detail'),
    path('risks/create/', login_required(role_required(['admin', 'safety_specialist'])(views.risk_create)),
         name='risk_create'),
    path('risks/<int:pk>/update/', login_required(role_required(['admin', 'safety_specialist'])(views.risk_update)),
         name='risk_update'),
    path('risks/<int:pk>/delete/', login_required(role_required(['admin', 'safety_specialist'])(views.risk_delete)),
         name='risk_delete'),
    path('risks/assessment/', login_required(role_required(['admin', 'safety_specialist'])(views.risk_assessment)),
         name='risk_assessment'),

    # Проверки - департамент только просмотр
    path('inspections/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.inspection_list)),
         name='inspection_list'),
    path('inspections/<int:pk>/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.inspection_detail)),
         name='inspection_detail'),
    path('inspections/create/', login_required(role_required(['admin', 'safety_specialist'])(views.inspection_create)),
         name='inspection_create'),
    path('inspections/<int:pk>/update/',
         login_required(role_required(['admin', 'safety_specialist'])(views.inspection_update)),
         name='inspection_update'),
    path('inspections/<int:pk>/delete/',
         login_required(role_required(['admin', 'safety_specialist'])(views.inspection_delete)),
         name='inspection_delete'),
    path('inspections/<int:pk>/complete/',
         login_required(role_required(['admin', 'safety_specialist'])(views.inspection_complete)),
         name='inspection_complete'),

    path('inspection_findings/create/<int:inspection_id>/',
         login_required(role_required(['admin', 'safety_specialist'])(views.inspection_finding_create)),
         name='inspection_finding_create'),
    path('inspection_findings/<int:pk>/update/',
         login_required(role_required(['admin', 'safety_specialist'])(views.inspection_finding_update)),
         name='inspection_finding_update'),
    path('inspection_findings/<int:pk>/delete/',
         login_required(role_required(['admin', 'safety_specialist'])(views.inspection_finding_delete)),
         name='inspection_finding_delete'),

    # Отчеты
    path('reports/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.report_list)),
         name='report_list'),
    path('reports/<str:report_type>/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.report_generate)),
         name='report_generate'),
    path('reports/custom/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.report_custom)),
         name='report_custom'),

    # URL для экспорта в различные форматы
    path('reports/inspection_results/excel/',
         views.inspection_results_report,
         {'format': 'excel'},
         name='inspection_results_excel'),

    path('reports/inspection_results/pdf/',
         views.inspection_results_report,
         {'format': 'pdf'},
         name='inspection_results_pdf'),

    # Сотрудники - специалист ОТ только просмотр
    path('employees/', login_required(
        role_required(['admin', 'department_head', 'medical_worker', 'safety_specialist'])(views.employee_list)),
         name='employee_list'),
    path('employees/<int:pk>/', login_required(
        role_required(['admin', 'department_head', 'medical_worker', 'safety_specialist'])(views.employee_detail)),
         name='employee_detail'),
    path('employees/create/', login_required(role_required(['admin', 'department_head'])(views.employee_create)),
         name='employee_create'),
    path('employees/<int:pk>/update/',
         login_required(role_required(['admin', 'department_head'])(views.employee_update)), name='employee_update'),
    path('employees/<int:pk>/delete/',
         login_required(role_required(['admin', 'department_head'])(views.employee_delete)), name='employee_delete'),

    path('reports/<str:report_type>/', views.report_generate, name='report_generate'),
    # Оборудование - департамент только просмотр
    path('equipment/', login_required(
        role_required(['admin', 'safety_specialist', 'department_head', 'technician'])(views.equipment_list)),
         name='equipment_list'),
    path('equipment/<int:pk>/', login_required(
        role_required(['admin', 'safety_specialist', 'department_head', 'technician'])(views.equipment_detail)),
         name='equipment_detail'),
    path('equipment/create/',
         login_required(role_required(['admin', 'safety_specialist', 'technician'])(views.equipment_create)),
         name='equipment_create'),
    path('equipment/<int:pk>/update/',
         login_required(role_required(['admin', 'safety_specialist', 'technician'])(views.equipment_update)),
         name='equipment_update'),
    path('equipment/<int:pk>/delete/',
         login_required(role_required(['admin', 'safety_specialist', 'technician'])(views.equipment_delete)),
         name='equipment_delete'),
    path('equipment/<int:pk>/maintenance/',
         login_required(role_required(['admin', 'safety_specialist', 'technician'])(views.equipment_maintenance)),
         name='equipment_maintenance'),

    # Обслуживание оборудования
    path('equipment_maintenance/',
         login_required(role_required(['admin', 'safety_specialist', 'technician'])(views.equipment_maintenance_list)),
         name='equipment_maintenance_list'),
    path('equipment_maintenance/<int:pk>/',
         login_required(role_required(['admin', 'safety_specialist', 'technician'])(views.maintenance_detail)),
         name='maintenance_detail'),
    path('equipment_maintenance/<int:pk>/update/',
         login_required(role_required(['admin', 'safety_specialist', 'technician'])(views.maintenance_update)),
         name='maintenance_update'),

    # Медицинские осмотры - только для админа и медика
    path('medical_exams/', login_required(role_required(['admin', 'medical_worker'])(views.medical_exam_list)),
         name='medical_exam_list'),
    path('medical_exams/<int:pk>/',
         login_required(role_required(['admin', 'medical_worker'])(views.medical_exam_detail)),
         name='medical_exam_detail'),
    path('medical_exams/create/', login_required(role_required(['admin', 'medical_worker'])(views.medical_exam_create)),
         name='medical_exam_create'),
    path('medical_exams/create/<int:employee_id>/',
         login_required(role_required(['admin', 'medical_worker'])(views.medical_exam_create)),
         name='medical_exam_create'),
    path('medical_exams/<int:pk>/update/',
         login_required(role_required(['admin', 'medical_worker'])(views.medical_exam_update)),
         name='medical_exam_update'),
    path('medical_exams/<int:pk>/delete/',
         login_required(role_required(['admin', 'medical_worker'])(views.medical_exam_delete)),
         name='medical_exam_delete'),

    # Уведомления - доступны всем авторизованным
    path('notifications/', login_required(views.notifications), name='notifications'),
    path('notifications/mark_read/<int:pk>/', login_required(views.notification_mark_read),
         name='notification_mark_read'),
    path('notifications/mark_all_read/', login_required(views.notifications_mark_all_read),
         name='notifications_mark_all_read'),

    # API для AJAX запросов
    path('api/stats/', login_required(views.api_stats), name='api_stats'),
    path('api/notifications/', login_required(views.api_notifications), name='api_notifications'),

    # Создание задач
    path('tasks/create/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.task_create)),
         name='task_create'),

    # Админ-панель - только для администратора
    path('admin/', orion_admin_site.urls),

    path('employees/send-medical-notifications/',
         login_required(role_required(['admin', 'medical_worker'])(views.send_medical_notifications)),
         name='send_medical_notifications'),

    path('prometheus/', include('django_prometheus.urls')),
    path('metrics/', views.metrics_view, name='metrics'),

    # Уведомления об эвакуации
    path('evacuation/create/',
         login_required(role_required(['admin', 'safety_specialist'])(views.evacuation_notification_create)),
         name='evacuation_create'),
    path('evacuation/cancel/<int:pk>/',
         login_required(role_required(['admin', 'safety_specialist'])(views.evacuation_cancel)),
         name='evacuation_cancel'),

    path('instructions/create-with-material/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.instruction_create_with_material)),
         name='instruction_create_with_material'),

    path('instructions/<int:pk>/add-materials/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.instruction_add_materials)),
         name='instruction_add_materials'),

    path('instructions/<int:pk>/add-test/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.instruction_add_test)),
         name='instruction_add_test'),

    path('instructions/test/<int:test_id>/add-question/',
         login_required(role_required(['admin', 'safety_specialist', 'department_head'])(views.instruction_add_test_question)),
         name='instruction_add_test_question'),

    path('instructions/material/<int:pk>/',
         login_required(views.instruction_material_detail),
         name='instruction_material_detail'),

    path('instructions/<int:pk>/study/',
         login_required(views.instruction_study),
         name='instruction_study'),

    path('instructions/test/<int:test_id>/take/',
         login_required(views.instruction_take_test),
         name='instruction_take_test'),

    path('instructions/test-result/<int:result_id>/',
         login_required(views.instruction_test_result),
         name='instruction_test_result'),

    path('instructions/test-results/',
         login_required(role_required(['admin', 'safety_specialist'])(views.instruction_test_results_list)),
         name='instruction_test_results_list'),

    path('instructions/test-result/<int:result_id>/review/',
         login_required(role_required(['admin', 'safety_specialist'])(views.instruction_review_test_result)),
         name='instruction_review_test_result'),

    # API для проверки уведомлений об эвакуации
    path('api/evacuation-check/', login_required(views.evacuation_check), name='api_evacuation_check'),

    # API для получения критических рисков
    path('api/critical-risks/', login_required(views.critical_risks_api), name='api_critical_risks'),

    # Управление критическими рисками
    path('risks/<int:pk>/resolve/',
         login_required(role_required(['admin', 'safety_specialist'])(views.risk_resolve)),
         name='risk_resolve'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)