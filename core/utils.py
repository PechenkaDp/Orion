import io
from datetime import timezone, timedelta

import xlsxwriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse


def generate_excel_report(data, title="Отчет"):
    """Генерирует отчет в формате Excel"""
    output = io.BytesIO()

    # Создаем новую рабочую книгу Excel и добавляем лист
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet("Отчет")

    # Форматирование для заголовков
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#FF7A00',
        'color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })

    # Форматирование для данных
    data_format = workbook.add_format({
        'border': 1
    })

    # Форматирование для итогов
    total_format = workbook.add_format({
        'bold': True,
        'bg_color': '#F8F8F8',
        'border': 1
    })

    # Пример данных для отчета проверок
    row = 0

    # Добавляем заголовок отчета
    worksheet.merge_range(row, 0, row, 7, title, header_format)
    row += 2

    # Заголовки колонок
    headers = ['Дата', 'Тип проверки', 'Подразделение', 'Инспектор', 'Нарушений', 'Устранено', 'Статус']
    for col, header in enumerate(headers):
        worksheet.write(row, col, header, header_format)

    # Записываем данные
    row += 1
    for inspection in data['inspections']:
        worksheet.write(row, 0, inspection['date'], data_format)
        worksheet.write(row, 1, inspection['type'], data_format)
        worksheet.write(row, 2, inspection['department'], data_format)
        worksheet.write(row, 3, inspection['inspector'], data_format)
        worksheet.write(row, 4, inspection['findings_count'], data_format)
        worksheet.write(row, 5, inspection['resolved_count'], data_format)
        worksheet.write(row, 6, inspection['status'], data_format)
        row += 1

    # Добавляем сводную информацию
    row += 2
    worksheet.merge_range(row, 0, row, 1, "Всего проверок:", total_format)
    worksheet.write(row, 2, data['inspections_count'], total_format)

    row += 1
    worksheet.merge_range(row, 0, row, 1, "Выявлено нарушений:", total_format)
    worksheet.write(row, 2, data['findings_count'], total_format)

    row += 1
    worksheet.merge_range(row, 0, row, 1, "Устранено нарушений:", total_format)
    worksheet.write(row, 2, f"{data['resolved_findings_percentage']}%", total_format)

    # Автоматически подгоняем ширину колонок
    for col_num, value in enumerate(headers):
        max_len = max(len(str(value)) + 2, 10)
        worksheet.set_column(col_num, col_num, max_len)

    workbook.close()

    # Возвращаем файл Excel
    output.seek(0)
    return output


def get_medical_exam_status(next_exam_date, warning_days=5):
    """
    Определяет статус медицинского осмотра на основе даты следующего осмотра.

    Args:
        next_exam_date: Дата следующего медосмотра
        warning_days: За сколько дней начинать предупреждать

    Returns:
        Строка: 'overdue', 'warning', 'normal' или 'none' если дата не установлена
    """
    if not next_exam_date:
        return 'none'

    current_date = timezone.now().date()
    warning_date = current_date + timedelta(days=warning_days)

    if next_exam_date < current_date:
        return 'overdue'  # Просрочено
    elif next_exam_date <= warning_date:
        return 'warning'  # Предупреждение
    else:
        return 'normal'  # В норме


def send_medical_exam_notification(employee, created_by=None):
    """
    Отправляет уведомление сотруднику о необходимости пройти медосмотр

    Args:
        employee: Объект Employee, которому отправляется уведомление
        created_by: Объект User, создавший уведомление (опционально)

    Returns:
        Объект созданного уведомления
    """
    from .models import Notification

    notification = Notification.objects.create(
        user=employee.user,
        title='Необходимо пройти медицинский осмотр',
        message=f'Вам необходимо пройти медицинский осмотр. Пожалуйста, обратитесь в медицинский отдел для согласования даты.',
        notification_type='medical',
        related_entity_type='employee',
        related_entity_id=employee.id,
        is_read=False
    )

    return notification


def generate_pdf_report(data, title="Отчет"):
    """Генерирует отчет в формате PDF"""
    buffer = io.BytesIO()

    # Создаем PDF документ
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []

    # Добавляем стили
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1  # По центру

    # Добавляем заголовок
    elements.append(Paragraph(title, title_style))
    elements.append(Paragraph(f"Период: {data['period']}", styles['Normal']))
    elements.append(Paragraph(f"Дата формирования: {data['report_date']}", styles['Normal']))
    elements.append(Paragraph(" ", styles['Normal']))  # Пустой отступ

    # Добавляем сводную информацию
    summary_data = [
        ["Всего проверок", str(data['inspections_count'])],
        ["Выявлено нарушений", str(data['findings_count'])],
        ["Устранено нарушений", f"{data['resolved_findings_percentage']}%"]
    ]

    summary_table = Table(summary_data, colWidths=[300, 150])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(summary_table)
    elements.append(Paragraph(" ", styles['Normal']))  # Пустой отступ

    # Данные для таблицы проверок
    table_data = [['Дата', 'Тип проверки', 'Подразделение', 'Нарушений', 'Устранено', 'Статус']]

    for inspection in data['inspections']:
        table_data.append([
            inspection['date'],
            inspection['type'],
            inspection['department'],
            str(inspection['findings_count']),
            str(inspection['resolved_count']),
            inspection['status']
        ])

    # Создаем таблицу и стилизуем ее
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)

    doc.build(elements)

    buffer.seek(0)
    return buffer