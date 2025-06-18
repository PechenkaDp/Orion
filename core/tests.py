from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import Employee, Department, Notification, Risk, Hazard, Inspection, InspectionFinding
import logging

logger = logging.getLogger(__name__)


class DashboardViewTest(TestCase):
    """Тесты для представления Dashboard"""

    def setUp(self):
        """Настройка начальных данных для тестов"""
        self.department = Department.objects.create(
            name='Test Department',
            description='Test Department Description'
        )

        self.employee_user = User.objects.create_user(
            username='employee',
            password='testpassword',
            first_name='John',
            last_name='Doe'
        )

        self.employee = Employee.objects.create(
            user=self.employee_user,
            department=self.department,
            position='Worker',
            role='employee',
            hire_date=timezone.now().date() - timedelta(days=365)
        )

        self.medical_user = User.objects.create_user(
            username='medical',
            password='testpassword',
            first_name='Jane',
            last_name='Smith'
        )

        self.medical_worker = Employee.objects.create(
            user=self.medical_user,
            position='Medical Worker',
            role='medical_worker',
            hire_date=timezone.now().date() - timedelta(days=730)
        )

        # 3. Создаем руководителя подразделения
        self.head_user = User.objects.create_user(
            username='head',
            password='testpassword',
            first_name='Robert',
            last_name='Brown'
        )

        self.department_head = Employee.objects.create(
            user=self.head_user,
            department=self.department,
            position='Department Head',
            role='department_head',
            hire_date=timezone.now().date() - timedelta(days=1095)
        )

        # Создаем тестовые данные для статистики
        self.hazard = Hazard.objects.create(
            name='Test Hazard',
            category='Physical'
        )

        self.risk = Risk.objects.create(
            hazard=self.hazard,
            department=self.department,
            level='medium',
            probability=0.5,
            severity=5,
            description='Test Risk',
            evaluated_by=self.head_user
        )

        # Проверка и нарушение
        self.inspection = Inspection.objects.create(
            title='Test Inspection',
            inspection_type='Regular',
            department=self.department,
            start_date=timezone.now() - timedelta(days=30),
            lead_inspector=self.head_user
        )

        self.finding = InspectionFinding.objects.create(
            inspection=self.inspection,
            description='Test Finding',
            severity='Medium',
            status='completed'
        )

        # Создаем уведомление
        self.notification = Notification.objects.create(
            user=self.employee_user,
            title='Test Notification',
            message='This is a test notification',
            notification_type='general',
            is_read=False
        )

        # Инициализируем клиента для тестирования
        self.client = Client()

    def test_dashboard_employee_authorized_access(self):
        """Тест, что авторизованный сотрудник может получить доступ к дашборду"""
        # Логинимся как сотрудник
        login_success = self.client.login(username='employee', password='testpassword')
        self.assertTrue(login_success, "Вход в систему должен быть успешным")

        # Получаем страницу дашборда
        response = self.client.get(reverse('dashboard'))

        # Проверяем, что доступ разрешен
        self.assertEqual(response.status_code, 200, "Авторизованный сотрудник должен иметь доступ к дашборду")

        # Проверяем, что используется правильный шаблон
        self.assertTemplateUsed(response, 'dashboard/dashboard.html')

        # Проверка наличия ключевых элементов в контексте
        self.assertIn('user_role', response.context, "Должна быть указана роль пользователя")
        self.assertIn('notification_count', response.context, "Должно быть указано количество уведомлений")

    def test_dashboard_medical_worker_authorized_access(self):
        """Тест, что авторизованный медицинский работник может получить доступ к дашборду"""
        # Логинимся как медицинский работник
        login_success = self.client.login(username='medical', password='testpassword')
        self.assertTrue(login_success, "Вход в систему должен быть успешным")

        # Получаем страницу дашборда
        response = self.client.get(reverse('dashboard'))

        # Проверяем, что доступ разрешен
        self.assertEqual(response.status_code, 200,
                         "Авторизованный медицинский работник должен иметь доступ к дашборду")

        # Проверяем наличие ключевых элементов в контексте
        self.assertIn('user_role', response.context, "Должна быть указана роль пользователя")
        self.assertIn('notification_count', response.context, "Должно быть указано количество уведомлений")

        # Проверяем, что пользователь существует и имеет правильную роль в модели
        db_employee = Employee.objects.get(user=self.medical_user)
        self.assertEqual(db_employee.role, 'medical_worker', "В базе данных должна быть установлена правильная роль")

    def test_dashboard_department_head_authorized_access(self):
        """Тест, что авторизованный руководитель подразделения может получить доступ к дашборду"""
        # Логинимся как руководитель подразделения
        login_success = self.client.login(username='head', password='testpassword')
        self.assertTrue(login_success, "Вход в систему должен быть успешным")

        # Получаем страницу дашборда
        response = self.client.get(reverse('dashboard'))

        # Проверяем, что доступ разрешен
        self.assertEqual(response.status_code, 200, "Авторизованный руководитель должен иметь доступ к дашборду")

        # Проверяем наличие ключевых элементов в контексте
        self.assertIn('user_role', response.context, "Должна быть указана роль пользователя")
        self.assertIn('notification_count', response.context, "Должно быть указано количество уведомлений")

        # Проверяем, что пользователь существует и имеет правильную роль в модели
        db_employee = Employee.objects.get(user=self.head_user)
        self.assertEqual(db_employee.role, 'department_head', "В базе данных должна быть установлена правильная роль")

    def test_dashboard_requires_authentication(self):
        """Тест, что дашборд требует аутентификации"""
        # Выходим из системы
        self.client.logout()

        # Пытаемся получить дашборд
        response = self.client.get(reverse('dashboard'))

        # Проверяем, что неавторизованный доступ вызывает редирект
        self.assertEqual(response.status_code, 302, "Неавторизованный доступ должен вызывать редирект")

        # Проверяем, что URL содержит параметр next с указанием на дашборд
        self.assertIn('next=', response.url, "URL должен содержать параметр next")
        self.assertIn('/dashboard/', response.url, "URL должен направлять на дашборд после логина")

    def test_notification_count_accuracy(self):
        """Тест точности счетчика уведомлений"""
        # Логинимся как сотрудник
        self.client.login(username='employee', password='testpassword')

        # Получаем страницу дашборда
        response = self.client.get(reverse('dashboard'))

        # Проверяем, что количество уведомлений соответствует созданному в setUp
        expected_count = Notification.objects.filter(user=self.employee_user, is_read=False).count()
        self.assertEqual(response.context['notification_count'], expected_count,
                         "Счетчик уведомлений должен показывать правильное число")

    def test_dashboard_contains_safety_statistics(self):
        """Тест наличия статистики безопасности на дашборде"""
        # Логинимся как сотрудник
        self.client.login(username='employee', password='testpassword')

        # Получаем страницу дашборда
        response = self.client.get(reverse('dashboard'))

        # Проверяем наличие ключевых показателей безопасности
        self.assertIn('identified_risks_count', response.context,
                      "Должно отображаться количество выявленных рисков")
        self.assertIn('compliance_percentage', response.context,
                      "Должен отображаться процент соответствия нормам")