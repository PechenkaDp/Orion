from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import (
    PPERequest, PPEIssuance, Instruction, Document, Equipment, EquipmentMaintenance,
    Risk, RiskMitigationMeasure, Inspection, InspectionFinding, Incident, SafetyTask,
    Employee, Department, InstructionType, Hazard, PPEItem, MedicalExamination, TestQuestion, TestAnswer,
    InstructionTest, InstructionMaterial
)


# Форма профиля пользователя
class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


# Форма регистрации пользователя с дополнительными полями
class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(UserRegisterForm, self).__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs={'class': 'form-control'})
        self.fields['password2'].widget = forms.PasswordInput(attrs={'class': 'form-control'})


# Форма сотрудника
class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'department', 'position', 'hire_date', 'medical_exam_date',
            'next_medical_exam_date', 'personal_id_number', 'emergency_contact', 'notes'
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'medical_exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'next_medical_exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'personal_id_number': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Форма заявки на СИЗ
class PPERequestForm(forms.ModelForm):
    class Meta:
        model = PPERequest
        fields = ['employee', 'ppe_item', 'quantity', 'notes']
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'ppe_item': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Форма выдачи СИЗ
class PPEIssuanceForm(forms.ModelForm):
    class Meta:
        model = PPEIssuance
        fields = [
            'employee', 'ppe_item', 'quantity', 'expected_return_date',
            'condition_on_issue', 'notes'
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'ppe_item': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'expected_return_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'condition_on_issue': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Форма проведения инструктажа
class InstructionForm(forms.ModelForm):
    class Meta:
        model = Instruction
        fields = [
            'instruction_type', 'department', 'instruction_date', 'next_instruction_date',
            'location', 'duration', 'notes'
        ]
        widgets = {
            'instruction_type': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'instruction_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'next_instruction_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Форма документа
class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            'title', 'document_type', 'file', 'description', 'publish_date',
            'effective_date', 'expiry_date', 'version', 'author', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'document_type': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'publish_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'effective_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'author': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# Форма оборудования
class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = [
            'name', 'equipment_type', 'model', 'serial_number', 'manufacturer',
            'purchase_date', 'warranty_expiry_date', 'department', 'location',
            'status', 'responsible_person', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'equipment_type': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'warranty_expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'responsible_person': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Форма обслуживания оборудования
class EquipmentMaintenanceForm(forms.ModelForm):
    class Meta:
        model = EquipmentMaintenance
        fields = [
            'maintenance_type', 'maintenance_date', 'description', 'result',
            'next_maintenance_date', 'documents_path', 'notes'
        ]
        widgets = {
            'maintenance_type': forms.TextInput(attrs={'class': 'form-control'}),
            'maintenance_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'result': forms.TextInput(attrs={'class': 'form-control'}),
            'next_maintenance_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'documents_path': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Форма риска
class RiskForm(forms.ModelForm):
    class Meta:
        model = Risk
        fields = [
            'hazard', 'department', 'location', 'level', 'probability', 'severity', 'description'
        ]
        widgets = {
            'hazard': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}),
            'probability': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 1, 'step': 0.1}),
            'severity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Форма мероприятия по снижению риска
class RiskMitigationMeasureForm(forms.ModelForm):
    class Meta:
        model = RiskMitigationMeasure
        fields = [
            'description', 'status', 'responsible_person', 'deadline', 'notes'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'responsible_person': forms.Select(attrs={'class': 'form-control'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Форма проверки
class InspectionForm(forms.ModelForm):
    class Meta:
        model = Inspection
        fields = [
            'title', 'inspection_type', 'department', 'start_date', 'end_date',
            'status', 'description'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'inspection_type': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Форма выявленного нарушения
class InspectionFindingForm(forms.ModelForm):
    class Meta:
        model = InspectionFinding
        fields = [
            'description', 'severity', 'location', 'responsible_department',
            'deadline', 'status', 'resolution'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'severity': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'responsible_department': forms.Select(attrs={'class': 'form-control'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'resolution': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Форма происшествия
class IncidentForm(forms.ModelForm):
    class Meta:
        model = Incident
        fields = [
            'title', 'incident_type', 'location', 'department', 'incident_date',
            'description', 'severity', 'immediate_actions'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'incident_type': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'incident_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'severity': forms.TextInput(attrs={'class': 'form-control'}),
            'immediate_actions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class MedicalExaminationForm(forms.ModelForm):
    class Meta:
        model = MedicalExamination
        fields = [
            'employee', 'exam_date', 'next_exam_date', 'exam_type',
            'medical_facility', 'doctor', 'result', 'recommendations',
            'restrictions', 'document', 'notes'
        ]
        widgets = {
            'employee': forms.Select(attrs={'class': 'form-control'}),
            'exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'next_exam_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'exam_type': forms.TextInput(attrs={'class': 'form-control'}),
            'medical_facility': forms.TextInput(attrs={'class': 'form-control'}),
            'doctor': forms.TextInput(attrs={'class': 'form-control'}),
            'result': forms.TextInput(attrs={'class': 'form-control'}),
            'recommendations': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'restrictions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'document': forms.FileInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class InstructionMaterialForm(forms.ModelForm):
    class Meta:
        model = InstructionMaterial
        fields = ['title', 'content', 'file', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class InstructionTestForm(forms.ModelForm):
    class Meta:
        model = InstructionTest
        fields = ['title', 'description', 'passing_score', 'time_limit', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TestQuestionForm(forms.ModelForm):
    class Meta:
        model = TestQuestion
        fields = ['question_text', 'order']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class TestAnswerForm(forms.ModelForm):
    class Meta:
        model = TestAnswer
        fields = ['answer_text', 'is_correct', 'order']
        widgets = {
            'answer_text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


TestAnswerFormSet = forms.inlineformset_factory(
    TestQuestion,
    TestAnswer,
    form=TestAnswerForm,
    extra=4,
    max_num=10,
    can_delete=True
)


class TestSubmissionForm(forms.Form):
    def __init__(self, test, *args, **kwargs):
        super(TestSubmissionForm, self).__init__(*args, **kwargs)

        # Add a field for each question
        for question in test.questions.all().order_by('order'):
            choices = [(answer.id, answer.answer_text) for answer in question.answers.all().order_by('order')]
            self.fields[f'question_{question.id}'] = forms.ChoiceField(
                label=question.question_text,
                choices=choices,
                widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                required=True
            )

# Форма задачи по охране труда
class SafetyTaskForm(forms.ModelForm):
    class Meta:
        model = SafetyTask
        fields = [
            'title', 'description', 'task_type', 'priority', 'status',
            'assigned_to', 'department', 'start_date', 'deadline', 'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'task_type': forms.TextInput(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}, choices=[
                ('low', 'Низкий'),
                ('medium', 'Средний'),
                ('high', 'Высокий'),
                ('critical', 'Критический')
            ]),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'deadline': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }