from faker import Faker
from locust import HttpUser, SequentialTaskSet, TaskSet, task, constant_throughput

fake = Faker('ru_RU')

departments = ["Производственный отдел", "Отдел безопасности", "Административный отдел", "ИТ-отдел", "Логистика"]
departments_added = []

safety_items = ["Защитная каска", "Респиратор", "Защитные очки", "Защитные перчатки", "Спецодежда"]
safety_items_added = []

document_types = ["Инструкция", "Регламент", "Положение", "Приказ", "Распоряжение"]
document_types_added = []

hazard_types = ["Химическая опасность", "Механическая опасность", "Электрическая опасность",
                "Пожарная опасность", "Радиационная опасность"]
hazard_types_added = []

inspection_types = ["Плановая", "Внеплановая", "Текущая", "Комплексная", "Целевая"]
inspection_types_added = []


class GetAuthRegister(TaskSet):
    @task
    def get_auth(self):
        response = self.client.get("/")
        if response.status_code != 200:
            response.failure("Не удалось загрузить страницу авторизации")

    @task
    def get_register(self):
        response = self.client.get("/admin/")
        if response.status_code != 200:
            response.failure("Не удалось загрузить страницу администратора")


class AdminLoginAndActions(TaskSet):
    def on_start(self):
        response = self.client.get("/")
        if "csrftoken" in response.cookies:
            csrftoken = response.cookies["csrftoken"]
            self.client.post("/", {
                "username": "admin",
                "password": "admin",
                "csrfmiddlewaretoken": csrftoken
            }, headers={"Referer": "http://127.0.0.1:8000/"})
        else:
            self.interrupt()

    @task
    def add_department(self):
        response = self.client.get("/admin/core/department/add/")

        if "csrftoken" in response.cookies:
            csrftoken = response.cookies["csrftoken"]

            department_name = departments[len(departments_added) % len(departments)]

            if department_name in departments_added:
                return

            self.client.post("/admin/core/department/add/", {
                "name": department_name,
                "description": fake.text(max_nb_chars=100),
                "csrfmiddlewaretoken": csrftoken
            }, headers={"Referer": "http://127.0.0.1:8000/admin/core/department/add/"})

            departments_added.append(department_name)

    @task
    def add_safety_item(self):
        response = self.client.get("/admin/core/ppeitem/add/")

        if "csrftoken" in response.cookies:
            csrftoken = response.cookies["csrftoken"]

            item_name = safety_items[len(safety_items_added) % len(safety_items)]

            if item_name in safety_items_added:
                return

            self.client.post("/admin/core/ppeitem/add/", {
                "name": item_name,
                "category": "Защита " + fake.word(),
                "standard_issue_period": fake.random_int(min=30, max=365),
                "csrfmiddlewaretoken": csrftoken
            }, headers={"Referer": "http://127.0.0.1:8000/admin/core/ppeitem/add/"})

            safety_items_added.append(item_name)

    @task
    def view_dashboard(self):
        self.client.get("/dashboard/")


class DocumentActions(TaskSet):
    def on_start(self):
        response = self.client.get("/")
        if "csrftoken" in response.cookies:
            csrftoken = response.cookies["csrftoken"]
            self.client.post("/", {
                "username": "admin",
                "password": "admin",
                "csrfmiddlewaretoken": csrftoken
            }, headers={"Referer": "http://127.0.0.1:8000/"})
        else:
            self.interrupt()

    @task
    def add_document(self):
        response = self.client.get("/documents/create/")

        if "csrfmiddlewaretoken" in response.text:
            csrftoken = response.text.split('name="csrfmiddlewaretoken" value="')[1].split('"')[0]

            doc_type = document_types[len(document_types_added) % len(document_types)]

            if doc_type in document_types_added:
                return

            self.client.post("/documents/create/", {
                "title": f"{doc_type} о {fake.word()}",
                "document_type": doc_type,
                "description": fake.text(max_nb_chars=150),
                "publish_date": fake.date(),
                "effective_date": fake.date(),
                "version": f"1.{fake.random_int(min=0, max=9)}",
                "author": fake.name(),
                "is_active": "on",
                "csrfmiddlewaretoken": csrftoken
            })

            document_types_added.append(doc_type)

    @task
    def view_documents(self):
        self.client.get("/documents/")


class RiskAndHazardActions(TaskSet):
    def on_start(self):
        response = self.client.get("/")
        if "csrftoken" in response.cookies:
            csrftoken = response.cookies["csrftoken"]
            self.client.post("/", {
                "username": "admin",
                "password": "admin",
                "csrfmiddlewaretoken": csrftoken
            }, headers={"Referer": "http://127.0.0.1:8000/"})
        else:
            self.interrupt()

    @task
    def add_hazard(self):
        response = self.client.get("/admin/core/hazard/add/")
        if "csrftoken" in response.cookies:
            csrftoken = response.cookies["csrftoken"]

            hazard_type = hazard_types[len(hazard_types_added) % len(hazard_types)]

            if hazard_type in hazard_types_added:
                return

            self.client.post("/admin/core/hazard/add/", {
                "name": hazard_type,
                "description": fake.text(max_nb_chars=150),
                "category": hazard_type.split()[0],
                "csrfmiddlewaretoken": csrftoken
            }, headers={"Referer": "http://127.0.0.1:8000/admin/core/hazard/add/"})

            hazard_types_added.append(hazard_type)

    @task
    def view_risks(self):
        self.client.get("/risks/")


class InspectionActions(TaskSet):
    def on_start(self):
        response = self.client.get("/")
        if "csrftoken" in response.cookies:
            csrftoken = response.cookies["csrftoken"]
            self.client.post("/", {
                "username": "admin",
                "password": "admin",
                "csrfmiddlewaretoken": csrftoken
            }, headers={"Referer": "http://127.0.0.1:8000/"})
        else:
            self.interrupt()

    @task
    def add_inspection(self):
        response = self.client.get("/inspections/create/")

        if "csrfmiddlewaretoken" in response.text:
            csrftoken = response.text.split('name="csrfmiddlewaretoken" value="')[1].split('"')[0]

            inspection_type = inspection_types[len(inspection_types_added) % len(inspection_types)]

            if inspection_type in inspection_types_added:
                return

            self.client.post("/inspections/create/", {
                "title": f"Проверка {fake.word()} ({inspection_type})",
                "inspection_type": inspection_type,
                "department": "1",
                "start_date": fake.date_time(),
                "status": "new",
                "description": fake.text(max_nb_chars=150),
                "csrfmiddlewaretoken": csrftoken
            })

            inspection_types_added.append(inspection_type)

    @task
    def view_inspections(self):
        self.client.get("/inspections/")


class WebsiteUser(HttpUser):
    tasks = [
        GetAuthRegister,
        AdminLoginAndActions,
        DocumentActions,
        RiskAndHazardActions,
        InspectionActions
    ]
    wait_time = constant_throughput(1)