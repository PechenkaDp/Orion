# middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class RoleBasedAccessMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

        # Карта доступа к URL-паттернам для каждой роли
        self.access_map = {
            'admin': ['*'],  # У администратора доступ ко всем страницам
            'safety_specialist': [
                'dashboard', 'search', 'profile', 'notification', 'api_',
                'ppe_', 'instruction_', 'document_', 'risk_', 'inspection_', 'report_', 'equipment_',
                'employee_list', 'employee_detail'  # Специалист ОТ может только просматривать сотрудников
            ],
            'department_head': [
                'dashboard', 'search', 'profile', 'notification', 'api_',
                'ppe_', 'instruction_', 'document_', 'employee_',
                'risk_list', 'risk_detail',  # Руководитель может только просматривать риски
                'inspection_list', 'inspection_detail',  # Руководитель может только просматривать проверки
                'equipment_list', 'equipment_detail'  # Руководитель может только просматривать оборудование
            ],
            'employee': [
                'dashboard', 'search', 'profile', 'notification', 'api_',
                'document_list', 'document_detail',  # Сотрудник может только просматривать документы
                'ppe_create', 'ppe_detail'  # Сотрудник может создавать заявки и смотреть детали своих заявок
            ],
            'medical_worker': [
                'dashboard', 'search', 'profile', 'notification', 'api_',
                'document_list', 'document_detail',  # Медик может только просматривать документы
                'employee_list', 'employee_detail',  # Медик может просматривать сотрудников
                'medical_'  # Медик имеет полный доступ к медосмотрам
            ],
            'technician': [
                'dashboard', 'search', 'profile', 'notification', 'api_',
                'equipment_', 'equipment_maintenance'  # Техник имеет полный доступ к оборудованию
            ],
        }

        # URL-адреса, доступные всем (в том числе неавторизованным пользователям)
        self.public_paths = [
            'login',
            'logout',
            'password_reset',
            'password_reset_done',
            'password_reset_confirm',
            'password_reset_complete',
        ]

        # Пути, исключенные из проверки доступа (для аутентифицированных пользователей)
        self.auth_paths = [
            'dashboard',  # Дашборд доступен всем авторизованным
            'profile',
            'search',
            'notifications',
            'notification_mark_read',
            'notifications_mark_all_read',
            'api_stats',
            'api_notifications',
        ]

    def __call__(self, request):
        if not request.user.is_authenticated:
            # Пропускаем неаутентифицированных пользователей (будет обработано auth middleware)
            return self.get_response(request)

        # Если путь не установлен, пропускаем проверку
        if not hasattr(request, 'resolver_match') or not request.resolver_match:
            return self.get_response(request)

        path_name = request.resolver_match.url_name if request.resolver_match else ''
        app_name = request.resolver_match.app_name if request.resolver_match else ''

        full_path = f"{app_name}:{path_name}" if app_name else path_name

        # Если путь публичный или входит в исключения для аутентифицированных, пропускаем проверку
        if path_name in self.public_paths or path_name in self.auth_paths:
            return self.get_response(request)

        # Если путь связан с административной панелью Django, пропускаем для админа или блокируем для других
        if full_path.startswith('admin:') or path_name.startswith('admin:'):
            try:
                if request.user.employee.role == 'admin':
                    return self.get_response(request)
                else:
                    messages.error(request, 'У вас нет доступа к административной панели.')
                    return redirect('dashboard')
            except:
                messages.error(request, 'У вас нет доступа к административной панели.')
                return redirect('dashboard')

        # Получаем роль пользователя
        try:
            employee = request.user.employee
            user_role = employee.role
        except Exception:
            user_role = 'employee'  # По умолчанию

        # Проверяем доступ на основе роли
        has_access = self.check_access(user_role, full_path)

        if not has_access:
            messages.error(request, 'У вас нет доступа к данной функции.')

            # Перенаправляем на дашборд, т.к. пользователь уже авторизован
            return redirect('dashboard')

        # Проверка специальных ограничений для определенных ролей
        if user_role == 'department_head':
            # Для руководителя департамента ограничиваем действия с рисками, проверками и оборудованием - только просмотр
            if (path_name.startswith('risk_') and path_name not in ['risk_list', 'risk_detail']) or \
                    (path_name.startswith('inspection_') and path_name not in ['inspection_list',
                                                                               'inspection_detail']) or \
                    (path_name.startswith('equipment_') and path_name not in ['equipment_list', 'equipment_detail']):
                messages.error(request, 'У вас есть доступ только для просмотра данного раздела.')
                # Перенаправляем на страницу списка соответствующего раздела
                if path_name.startswith('risk_'):
                    return redirect('risk_list')
                elif path_name.startswith('inspection_'):
                    return redirect('inspection_list')
                elif path_name.startswith('equipment_'):
                    return redirect('equipment_list')

        if user_role == 'safety_specialist':
            # Для специалиста ОТ ограничиваем действия с сотрудниками - только просмотр
            if path_name.startswith('employee_') and path_name not in ['employee_list', 'employee_detail']:
                messages.error(request, 'У вас есть доступ только для просмотра данного раздела.')
                return redirect('employee_list')

        if user_role == 'employee':
            # Для обычного сотрудника ограничиваем действия с документами - только просмотр
            if path_name.startswith('document_') and path_name not in ['document_list', 'document_detail']:
                messages.error(request, 'У вас есть доступ только для просмотра документов.')
                return redirect('document_list')

        if user_role == 'medical_worker':
            # Для медработника ограничиваем действия с документами и сотрудниками - только просмотр
            if path_name.startswith('document_') and path_name not in ['document_list', 'document_detail']:
                messages.error(request, 'У вас есть доступ только для просмотра документов.')
                return redirect('document_list')
            elif path_name.startswith('employee_') and path_name not in ['employee_list', 'employee_detail']:
                messages.error(request, 'У вас есть доступ только для просмотра данных сотрудников.')
                return redirect('employee_list')

        response = self.get_response(request)
        return response

    def check_access(self, role, path):
        """Проверка доступа пользователя к URL на основе роли"""
        if role not in self.access_map:
            return False

        allowed_paths = self.access_map[role]

        # Для администратора разрешен доступ ко всему
        if '*' in allowed_paths:
            return True

        # Проверяем, есть ли у роли доступ к данному пути
        for allowed_path in allowed_paths:
            if path == allowed_path or path.startswith(allowed_path):
                return True

        return False