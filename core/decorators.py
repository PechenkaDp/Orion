from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def role_required(allowed_roles):
    """
    Декоратор, который проверяет роль пользователя и разрешает доступ только определенным ролям.

    Пример использования:
    @role_required(['admin', 'safety_specialist'])
    def some_view(request):
        # обработка представления
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            try:
                user_role = request.user.employee.role
            except:
                user_role = 'employee'  # По умолчанию

            if user_role not in allowed_roles:
                messages.error(request, 'У вас нет доступа к данному разделу системы.')
                return redirect('dashboard')

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def view_only_permission(original_view):
    """
    Декоратор, который разрешает только просмотр (GET-запросы) и запрещает изменения.
    Используется для представлений, где некоторые роли могут только просматривать данные.
    """

    @wraps(original_view)
    def _wrapped_view(request, *args, **kwargs):
        if request.method != 'GET':
            messages.error(request, 'У вас есть доступ только для просмотра данного раздела.')
            return redirect('dashboard')
        return original_view(request, *args, **kwargs)

    return _wrapped_view