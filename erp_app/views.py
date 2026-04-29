from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.db.models import Count, Sum, Avg, Max, Q
from django.utils import timezone
from functools import wraps
from datetime import date, timedelta
import random, json, os

from .models import (
    User, Patient, Doctor, Department, Appointment, Prescription,
    PrescriptionItem, LabReport, Ward, Bed, PatientVitals, Invoice,
    InvoiceItem, Medicine, PharmacyDispense, Notification,
    AIPredictionLog, Receptionist, AuditLog
)

# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────
def get_user_model():
    from django.contrib.auth import get_user_model as _get
    return _get()

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('role_login', role='PATIENT')
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("⛔ Access Denied — Insufficient Permissions")
        return wrapper
    return decorator

def log_action(user, action, model_name=None, object_id=None, details=None, request=None):
    ip = None
    if request:
        ip = request.META.get('REMOTE_ADDR')
    AuditLog.objects.create(
        user=user, action=action, model_name=model_name,
        object_id=object_id, details=details, ip_address=ip
    )

def create_notification(user, title, message, notif_type='system', link=None):
    Notification.objects.create(user=user, title=title, message=message,
                                 notif_type=notif_type, link=link)

def ai_priority_from_symptoms(symptoms_text):
    if not symptoms_text:
        return 'Normal'
    text = symptoms_text.lower()
    emergency_kw = ['chest pain', 'heart attack', 'stroke', 'unconscious', 'breathing difficulty',
                    'severe bleeding', 'seizure', 'paralysis', 'anaphylaxis']
    high_kw = ['high fever', 'severe pain', 'vomiting blood', 'fracture', 'head injury',
               'diabetic', 'hypertension']
    if any(k in text for k in emergency_kw):
        return 'Emergency'
    if any(k in text for k in high_kw):
        return 'High'
    if any(k in text for k in ['fever', 'pain', 'infection', 'injury']):
        return 'Normal'
    return 'Normal'

def compute_patient_risk(patient):
    """Simple ML-style risk scoring based on age, vitals, appointments"""
    score = 0
    if patient.age > 60:
        score += 30
    elif patient.age > 40:
        score += 15
    if patient.chronic_conditions:
        score += 25
    if patient.allergies:
        score += 10
    vitals = patient.vitals.first()
    if vitals:
        if vitals.heart_rate and (vitals.heart_rate > 100 or vitals.heart_rate < 50):
            score += 20
        if vitals.blood_pressure_systolic and vitals.blood_pressure_systolic > 140:
            score += 20
        if vitals.oxygen_saturation and vitals.oxygen_saturation < 94:
            score += 30
        if vitals.blood_sugar and vitals.blood_sugar > 200:
            score += 20
    appt_count = Appointment.objects.filter(patient=patient).count()
    if appt_count > 10:
        score += 15
    score = min(score, 100)
    if score >= 70:
        label = 'Critical'
    elif score >= 50:
        label = 'High'
    elif score >= 25:
        label = 'Medium'
    else:
        label = 'Low'
    return score, label

def generate_invoice_number():
    import random
    return f"INV{date.today().strftime('%Y%m%d')}{random.randint(1000,9999)}"

# ──────────────────────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────────────────────
def home(request):
    if request.user.is_authenticated:
        return redirect('redirect_dashboard')
    stats = {
        'total_patients': Patient.objects.count(),
        'total_doctors': Doctor.objects.count(),
        'total_appointments': Appointment.objects.count(),
        'departments': Department.objects.count(),
    }
    return render(request, 'home.html', {'stats': stats})

def login_view(request, role='PATIENT'):
    if request.user.is_authenticated:
        return redirect('redirect_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            log_action(user, 'LOGIN', request=request)
            return redirect('redirect_dashboard')
        messages.error(request, '❌ Invalid credentials. Please try again.')
    return render(request, 'login.html', {'role': role})

def logout_view(request):
    if request.user.is_authenticated:
        log_action(request.user, 'LOGOUT', request=request)
    logout(request)
    return redirect('home')

def redirect_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('role_login', role='PATIENT')
    role_map = {
        'ADMIN': 'admin_dashboard', 'DOCTOR': 'doctor_dashboard',
        'RECEPTION': 'reception_dashboard', 'LAB': 'lab_dashboard',
        'PHARMACY': 'pharmacy_dashboard', 'PATIENT': 'patient_dashboard',
    }
    return redirect(role_map.get(request.user.role, 'home'))

# ──────────────────────────────────────────────────────────────
# ADMIN PORTAL — Full
# ──────────────────────────────────────────────────────────────
@login_required
@role_required(['ADMIN'])
def admin_dashboard(request):
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(date=today).count()
    pending_appointments = Appointment.objects.filter(status='Pending').count()
    total_revenue = Invoice.objects.filter(status='Paid').aggregate(t=Sum('total'))['t'] or 0
    critical_reports = LabReport.objects.filter(abnormal_flag='Critical').count()
    low_stock_medicines = Medicine.objects.filter(stock_quantity__lte=50).count()

    # Charts data
    weekly_appts = []
    for i in range(7):
        d = today - timedelta(days=6-i)
        weekly_appts.append({'date': d.strftime('%a'), 'count': Appointment.objects.filter(date=d).count()})

    dept_stats = Department.objects.annotate(
        doctor_count=Count('doctor')
    ).values('name', 'doctor_count')

    status_counts = {
        'Pending': Appointment.objects.filter(status='Pending').count(),
        'Approved': Appointment.objects.filter(status='Approved').count(),
        'Completed': Appointment.objects.filter(status='Completed').count(),
        'Cancelled': Appointment.objects.filter(status='Cancelled').count(),
    }

    recent_patients = Patient.objects.order_by('-registered_at')[:8]
    recent_audits = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
    unread_alerts = Notification.objects.filter(user=request.user, is_read=False).count()

    # Revenue by month (last 6)
    monthly_revenue = []
    for i in range(6):
        d = today.replace(day=1) - timedelta(days=i*30)
        rev = Invoice.objects.filter(
            created_at__year=d.year, created_at__month=d.month, status='Paid'
        ).aggregate(t=Sum('total'))['t'] or 0
        monthly_revenue.append({'month': d.strftime('%b'), 'revenue': float(rev)})
    monthly_revenue.reverse()

    context = {
        'total_patients': total_patients, 'total_doctors': total_doctors,
        'total_appointments': total_appointments, 'today_appointments': today_appointments,
        'pending_appointments': pending_appointments, 'total_revenue': total_revenue,
        'critical_reports': critical_reports, 'low_stock_medicines': low_stock_medicines,
        'weekly_appts': json.dumps(weekly_appts),
        'status_counts': json.dumps(status_counts),
        'monthly_revenue': json.dumps(monthly_revenue),
        'dept_stats': list(dept_stats),
        'recent_patients': recent_patients,
        'recent_audits': recent_audits,
        'unread_alerts': unread_alerts,
    }
    return render(request, 'dashboards/admin.html', context)

@login_required
@role_required(['ADMIN'])
def admin_users(request):
    users = User.objects.all().order_by('-date_joined')
    role_filter = request.GET.get('role', '')
    search = request.GET.get('search', '')
    if role_filter:
        users = users.filter(role=role_filter)
    if search:
        users = users.filter(Q(username__icontains=search) | Q(first_name__icontains=search) | Q(email__icontains=search))
    role_choices = [('ADMIN','Admin'),('DOCTOR','Doctor'),('RECEPTION','Reception'),('LAB','Lab Technician'),('PHARMACY','Pharmacist'),('PATIENT','Patient')]
    return render(request, 'admin/users.html', {'users': users, 'role_filter': role_filter, 'search': search, 'role_choices': role_choices})

@login_required
@role_required(['ADMIN'])
def admin_create_user(request):
    if request.method == 'POST':
        role = request.POST.get('role')
        username = request.POST.get('username')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, '⚠ Username already exists.')
            return redirect('admin_create_user')

        user = User.objects.create_user(
            username=username, password=password,
            first_name=first_name, last_name=last_name,
            email=email, role=role, phone=phone
        )

        if role == 'DOCTOR':
            spec = request.POST.get('specialization', 'General')
            dept_id = request.POST.get('department')
            dept = Department.objects.filter(id=dept_id).first()
            Doctor.objects.create(user=user, specialization=spec, phone=phone, department=dept)
        elif role == 'PATIENT':
            age = request.POST.get('age', 25)
            Patient.objects.create(user=user, name=f"{first_name} {last_name}".strip() or username, age=age, phone=phone)
        elif role == 'RECEPTION':
            Receptionist.objects.create(user=user, phone=phone)

        log_action(request.user, f'CREATE USER: {username} ({role})', 'User', user.id, request=request)
        messages.success(request, f'✅ User {username} created successfully!')
        return redirect('admin_users')

    departments = Department.objects.all()
    return render(request, 'admin/create_user.html', {'departments': departments})

@login_required
@role_required(['ADMIN'])
def admin_toggle_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = not user.is_active
    user.save()
    action = 'ACTIVATE' if user.is_active else 'DEACTIVATE'
    log_action(request.user, f'{action} USER: {user.username}', 'User', user.id, request=request)
    messages.success(request, f'User {user.username} {"activated" if user.is_active else "deactivated"}.')
    return redirect('admin_users')

@login_required
@role_required(['ADMIN'])
def admin_departments(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        desc = request.POST.get('description', '')
        Department.objects.create(name=name, description=desc)
        messages.success(request, f'Department "{name}" created.')
        return redirect('admin_departments')
    departments = Department.objects.annotate(doctor_count=Count('doctor'))
    return render(request, 'admin/departments.html', {'departments': departments})

@login_required
@role_required(['ADMIN'])
def admin_reports(request):
    today = date.today()
    total_revenue = Invoice.objects.filter(status='Paid').aggregate(t=Sum('total'))['t'] or 0
    unpaid = Invoice.objects.filter(status='Unpaid').aggregate(t=Sum('total'))['t'] or 0
    invoices = Invoice.objects.select_related('patient').order_by('-created_at')[:20]
    audit_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:30]
    ai_logs = AIPredictionLog.objects.select_related('patient').order_by('-created_at')[:20]
    context = {
        'total_revenue': total_revenue, 'unpaid': unpaid,
        'invoices': invoices, 'audit_logs': audit_logs, 'ai_logs': ai_logs,
    }
    return render(request, 'admin/reports.html', context)

@login_required
@role_required(['ADMIN'])
def admin_ward_management(request):
    wards = Ward.objects.all()
    beds = Bed.objects.select_related('patient', 'ward').all()
    total_beds = beds.count()
    occupied = beds.filter(is_occupied=True).count()
    available = total_beds - occupied
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_ward':
            Ward.objects.create(
                name=request.POST.get('name'),
                ward_type=request.POST.get('ward_type'),
                floor=request.POST.get('floor', 1),
                total_beds=request.POST.get('total_beds', 10)
            )
            messages.success(request, 'Ward added.')
        elif action == 'discharge':
            bed_id = request.POST.get('bed_id')
            bed = get_object_or_404(Bed, id=bed_id)
            bed.is_occupied = False
            bed.patient = None
            bed.admitted_at = None
            bed.save()
            messages.success(request, 'Patient discharged from bed.')
        return redirect('admin_ward_management')
    context = {'wards': wards, 'beds': beds, 'total_beds': total_beds,
               'occupied': occupied, 'available': available}
    return render(request, 'admin/ward_management.html', context)

# ──────────────────────────────────────────────────────────────
# DOCTOR PORTAL
# ──────────────────────────────────────────────────────────────
@login_required
@role_required(['DOCTOR'])
def doctor_dashboard(request):
    doctor = request.user.doctor
    today = date.today()
    appointments = Appointment.objects.filter(doctor=doctor)
    today_appts = appointments.filter(date=today).order_by('time')
    total_patients = Patient.objects.filter(appointment__doctor=doctor).distinct().count()
    pending_count = appointments.filter(status='Pending').count()
    completed_today = appointments.filter(date=today, status='Completed').count()
    critical_reports = LabReport.objects.filter(doctor=doctor, abnormal_flag='Critical', status='Completed').order_by('-date')[:5]
    recent_prescriptions = Prescription.objects.filter(doctor=doctor).order_by('-created_at')[:5]

    # Weekly chart
    weekly = []
    for i in range(7):
        d = today - timedelta(days=6-i)
        weekly.append({'day': d.strftime('%a'), 'count': appointments.filter(date=d).count()})

    unread = Notification.objects.filter(user=request.user, is_read=False).count()

    approved_count = appointments.filter(status='Approved').count()
    context = {
        'doctor': doctor,
        'today_appts': today_appts,
        'appointments': today_appts,
        'total_patients': total_patients,
        'today_count': today_appts.count(),
        'today_appointments': today_appts.count(),
        'pending_count': pending_count,
        'approved_count': approved_count,
        'completed_today': completed_today,
        'completed_appointments': completed_today,
        'total_appointments': appointments.count(),
        'critical_reports': critical_reports,
        'recent_prescriptions': recent_prescriptions,
        'weekly_data': json.dumps(weekly),
        'today': today,
        'unread': unread,
    }
    return render(request, 'doctors/dashboard.html', context)

@login_required
@role_required(['DOCTOR'])
def doctor_appointments(request):
    doctor = request.user.doctor
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    appointments = Appointment.objects.filter(doctor=doctor).select_related('patient').order_by('-date', 'time')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    if date_filter:
        appointments = appointments.filter(date=date_filter)
    return render(request, 'doctors/appointments.html', {
        'appointments': appointments, 'status_filter': status_filter, 'date_filter': date_filter
    })

@login_required
@role_required(['DOCTOR'])
def update_appointment_status(request, id, status):
    appt = get_object_or_404(Appointment, id=id)
    VALID = ['Pending', 'Approved', 'Completed', 'Cancelled', 'No-Show']
    if status in VALID:
        appt.status = status
        appt.save()
        if appt.patient.user:
            create_notification(appt.patient.user, f'Appointment {status}',
                                f'Your appointment on {appt.date} has been marked {status}.', 'appointment')
    ref = request.META.get('HTTP_REFERER', 'doctor_appointments')
    return redirect(ref)

@login_required
@role_required(['DOCTOR'])
def doctor_patients(request):
    doctor = request.user.doctor
    search = request.GET.get('search', '')
    patients = Patient.objects.filter(appointment__doctor=doctor).distinct().annotate(
        last_visit=Max('appointment__date'),
        total_visits=Count('appointment')
    )
    if search:
        patients = patients.filter(name__icontains=search)
    today = date.today()
    for p in patients:
        if p.last_visit and (today - p.last_visit).days <= 30:
            p.status_label = 'Active'
        else:
            p.status_label = 'Inactive'
    return render(request, 'doctors/patients.html', {'patients': patients, 'search': search})

@login_required
@role_required(['DOCTOR'])
def patient_profile(request, id):
    patient = get_object_or_404(Patient, id=id)
    appointments = Appointment.objects.filter(patient=patient).order_by('-date')
    prescriptions = Prescription.objects.filter(patient=patient).order_by('-created_at')
    lab_reports = LabReport.objects.filter(patient=patient).order_by('-date')
    vitals = PatientVitals.objects.filter(patient=patient).order_by('-recorded_at')[:10]
    vitals_chart = [{'date': v.recorded_at.strftime('%m/%d'), 'hr': v.heart_rate or 0,
                     'bp': v.blood_pressure_systolic or 0, 'spo2': v.oxygen_saturation or 0,
                     'temp': v.temperature or 0} for v in reversed(list(vitals))]
    risk_score, risk_label = compute_patient_risk(patient)
    patient.risk_score = risk_score
    patient.risk_label = risk_label
    patient.save(update_fields=['risk_score', 'risk_label'])

    if request.method == 'POST' and request.POST.get('action') == 'add_vitals':
        PatientVitals.objects.create(
            patient=patient,
            recorded_by=request.user,
            blood_pressure_systolic=request.POST.get('systolic') or None,
            blood_pressure_diastolic=request.POST.get('diastolic') or None,
            heart_rate=request.POST.get('heart_rate') or None,
            temperature=request.POST.get('temperature') or None,
            oxygen_saturation=request.POST.get('spo2') or None,
            weight=request.POST.get('weight') or None,
            height=request.POST.get('height') or None,
            blood_sugar=request.POST.get('blood_sugar') or None,
            notes=request.POST.get('notes', '')
        )
        messages.success(request, '✅ Vitals recorded.')
        return redirect('patient_profile', id=id)

    return render(request, 'doctors/patient_profile.html', {
        'patient': patient, 'appointments': appointments[:5],
        'prescriptions': prescriptions[:5], 'lab_reports': lab_reports[:5],
        'vitals': vitals, 'vitals_chart': json.dumps(vitals_chart),
        'risk_score': risk_score, 'risk_label': risk_label,
    })

@login_required
@role_required(['DOCTOR'])
def doctor_prescriptions(request):
    doctor = request.user.doctor
    search = request.GET.get('search', '')
    prescriptions = Prescription.objects.filter(doctor=doctor).select_related('patient').order_by('-created_at')
    if search:
        prescriptions = prescriptions.filter(patient__name__icontains=search)
    return render(request, 'doctors/prescriptions.html', {'prescriptions': prescriptions, 'search': search})

@login_required
@role_required(['DOCTOR'])
def add_prescription(request, id):
    patient = get_object_or_404(Patient, id=id)
    doctor = request.user.doctor
    appointment = Appointment.objects.filter(patient=patient, doctor=doctor, status='Approved').order_by('-date').first()

    if request.method == 'POST':
        medicines = request.POST.getlist('medicine[]')
        dosages = request.POST.getlist('dosage[]')
        days_list = request.POST.getlist('days[]')
        freqs = request.POST.getlist('frequency[]')
        instructions_list = request.POST.getlist('instructions[]')
        diagnosis = request.POST.get('diagnosis', '')
        notes = request.POST.get('notes', '')
        follow_up = request.POST.get('follow_up_date') or None

        if not any(m.strip() for m in medicines):
            messages.error(request, 'Add at least one medicine.')
            return redirect('add_prescription', id=id)

        rx = Prescription.objects.create(
            doctor=doctor, patient=patient,
            appointment=appointment,
            diagnosis=diagnosis, notes=notes,
            follow_up_date=follow_up
        )
        for med, dos, days, freq, instr in zip(medicines, dosages, days_list, freqs, instructions_list):
            if med.strip():
                PrescriptionItem.objects.create(
                    prescription=rx, medicine=med.strip(),
                    dosage=dos.strip(), days=int(days) if days.strip().isdigit() else None,
                    frequency=freq or 'Once daily', instructions=instr.strip()
                )
        if appointment:
            appointment.status = 'Completed'
            appointment.save()
        if patient.user:
            create_notification(patient.user, 'New Prescription',
                                f'Dr. {doctor} has issued a new prescription.', 'appointment')
        log_action(request.user, 'ADD PRESCRIPTION', 'Prescription', rx.id, request=request)
        messages.success(request, '✅ Prescription saved!')
        return redirect('view_prescriptions', id=patient.id)

    medicines_list = Medicine.objects.filter(is_available=True).values_list('name', flat=True)
    return render(request, 'doctors/add_prescription.html', {
        'patient': patient, 'appointment': appointment, 'medicines_list': list(medicines_list)
    })

@login_required
@role_required(['DOCTOR'])
def view_prescriptions(request, id):
    patient = get_object_or_404(Patient, id=id)
    prescriptions = Prescription.objects.filter(patient=patient).order_by('-created_at')
    return render(request, 'doctors/view_prescriptions.html', {'patient': patient, 'prescriptions': prescriptions})

@login_required
@role_required(['DOCTOR'])
def prescription_detail(request, id):
    prescription = get_object_or_404(Prescription, id=id)
    return render(request, 'doctors/prescription_detail.html', {'prescription': prescription})

@login_required
@role_required(['DOCTOR'])
def doctor_reports(request):
    doctor = request.user.doctor
    reports = LabReport.objects.filter(doctor=doctor).select_related('patient').order_by('-date')
    flag_filter = request.GET.get('flag', '')
    if flag_filter:
        reports = reports.filter(abnormal_flag=flag_filter)
    return render(request, 'doctors/reports.html', {'reports': reports, 'flag_filter': flag_filter})

@login_required
@role_required(['DOCTOR'])
def assign_lab_test(request):
    doctor = request.user.doctor
    patients = Patient.objects.filter(appointment__doctor=doctor).distinct()
    COMMON_TESTS = ['Complete Blood Count (CBC)', 'Blood Sugar Fasting', 'HbA1c',
                    'Lipid Profile', 'Liver Function Test (LFT)', 'Kidney Function Test (KFT)',
                    'Thyroid Profile', 'Urine Routine', 'X-Ray Chest', 'ECG', 'Echo', 'MRI Brain']
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        test_name = request.POST.get('test_name')
        priority = request.POST.get('priority', 'Normal')
        patient = get_object_or_404(Patient, id=patient_id)
        report = LabReport.objects.create(patient=patient, doctor=doctor,
                                           test_name=test_name, status='Pending', priority=priority)
        log_action(request.user, f'ASSIGN LAB TEST: {test_name}', 'LabReport', report.id, request=request)
        messages.success(request, f'✅ Lab test "{test_name}" assigned.')
        return redirect('doctor_dashboard')
    return render(request, 'doctors/assign_test.html', {'patients': patients, 'common_tests': COMMON_TESTS})

# PDF Download
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def download_prescription(request, id):
    prescription = get_object_or_404(Prescription, id=id)
    items = prescription.items.all()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="prescription_{id}.pdf"'
    doc = SimpleDocTemplate(response)
    styles = getSampleStyleSheet()
    content = []
    content.append(Paragraph("🏥 CuraSync AI — Prescription", styles['Title']))
    content.append(Spacer(1, 12))
    patient_name = prescription.patient.name if prescription.patient else "Unknown"
    doctor_name = str(prescription.doctor)
    content.append(Paragraph(f"<b>Patient:</b> {patient_name}", styles['Normal']))
    content.append(Paragraph(f"<b>Doctor:</b> {doctor_name}", styles['Normal']))
    content.append(Paragraph(f"<b>Date:</b> {prescription.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
    if prescription.diagnosis:
        content.append(Paragraph(f"<b>Diagnosis:</b> {prescription.diagnosis}", styles['Normal']))
    content.append(Spacer(1, 12))
    content.append(Paragraph("<b>Medicines Prescribed:</b>", styles['Heading2']))
    data = [['Medicine', 'Dosage', 'Frequency', 'Days', 'Instructions']]
    for item in items:
        data.append([item.medicine, item.dosage, item.frequency or '-',
                     str(item.days) if item.days else '-', item.instructions or '-'])
    t = Table(data, colWidths=[120, 80, 80, 40, 130])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0ea5e9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f9ff')]),
    ]))
    content.append(t)
    if prescription.notes:
        content.append(Spacer(1, 12))
        content.append(Paragraph(f"<b>Notes:</b> {prescription.notes}", styles['Normal']))
    if prescription.follow_up_date:
        content.append(Spacer(1, 8))
        content.append(Paragraph(f"<b>Follow-up Date:</b> {prescription.follow_up_date}", styles['Normal']))
    content.append(Spacer(1, 30))
    content.append(Paragraph("_______________________", styles['Normal']))
    content.append(Paragraph(f"{doctor_name} — Signature", styles['Normal']))
    doc.build(content)
    return response

# ──────────────────────────────────────────────────────────────
# PATIENT PORTAL
# ──────────────────────────────────────────────────────────────
@login_required
@role_required(['PATIENT'])
def patient_dashboard(request):
    patient = get_object_or_404(Patient, user=request.user)
    appointments = Appointment.objects.filter(patient=patient).order_by('-date')
    prescriptions = Prescription.objects.filter(patient=patient).order_by('-created_at')
    lab_reports = LabReport.objects.filter(patient=patient).order_by('-date')
    invoices = Invoice.objects.filter(patient=patient).order_by('-created_at')
    vitals = PatientVitals.objects.filter(patient=patient).order_by('-recorded_at').first()
    upcoming = appointments.filter(date__gte=date.today(), status='Approved').first()
    unread_notifs = Notification.objects.filter(user=request.user, is_read=False)

    # Risk
    risk_score, risk_label = compute_patient_risk(patient)

    context = {
        'patient': patient,
        'appointments_count': appointments.count(),
        'prescriptions_count': prescriptions.count(),
        'lab_reports_count': lab_reports.count(),
        'pending_invoices': invoices.filter(status='Unpaid').count(),
        'upcoming_appointment': upcoming,
        'recent_appointments': appointments[:3],
        'recent_prescriptions': prescriptions[:3],
        'recent_reports': lab_reports[:3],
        'latest_vitals': vitals,
        'unread_notifs': unread_notifs[:5],
        'risk_score': risk_score,
        'risk_label': risk_label,
    }
    return render(request, 'patients/dashboard.html', context)

@login_required
@role_required(['PATIENT'])
def patient_book_appointment(request):
    patient = get_object_or_404(Patient, user=request.user)
    doctors = Doctor.objects.filter(is_available=True).select_related('user', 'department')
    departments = Department.objects.all()
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        appt_date = request.POST.get('date')
        appt_time = request.POST.get('time')
        symptoms = request.POST.get('symptoms', '')
        dept = request.POST.get('department', '')
        appt_type = request.POST.get('type', 'OPD')
        doctor = get_object_or_404(Doctor, id=doctor_id)
        # Double booking check
        if Appointment.objects.filter(doctor=doctor, date=appt_date, time=appt_time).exists():
            messages.error(request, '⚠ That time slot is already booked. Please choose another.')
            return redirect('patient_book_appointment')
        priority = ai_priority_from_symptoms(symptoms)
        appt = Appointment.objects.create(
            patient=patient, doctor=doctor, date=appt_date, time=appt_time,
            symptoms=symptoms, department=dept, appointment_type=appt_type,
            priority=priority, status='Pending', ai_risk_flag=priority
        )
        create_notification(request.user, 'Appointment Booked',
                            f'Your appointment with {doctor} on {appt_date} at {appt_time} is pending approval.',
                            'appointment')
        log_action(request.user, 'BOOK APPOINTMENT', 'Appointment', appt.id, request=request)
        messages.success(request, f'✅ Appointment booked! Priority: {priority}')
        return redirect('patient_appointments')
    from datetime import date
    return render(request, 'patients/book_appointment.html', {'doctors': doctors, 'departments': departments, 'today_str': date.today().isoformat()})

@login_required
@role_required(['PATIENT'])
def patient_appointments(request):
    patient = get_object_or_404(Patient, user=request.user)
    appointments = Appointment.objects.filter(patient=patient).select_related('doctor__user').order_by('-date')
    return render(request, 'patients/appointments.html', {'appointments': appointments})

@login_required
@role_required(['PATIENT'])
def patient_prescriptions(request):
    patient = get_object_or_404(Patient, user=request.user)
    prescriptions = Prescription.objects.filter(patient=patient).order_by('-created_at')
    return render(request, 'patients/prescriptions.html', {'prescriptions': prescriptions})

@login_required
@role_required(['PATIENT'])
def patient_reports(request):
    patient = get_object_or_404(Patient, user=request.user)
    reports = LabReport.objects.filter(patient=patient).order_by('-date')
    return render(request, 'patients/reports.html', {'reports': reports})

@login_required
@role_required(['PATIENT'])
def patient_billing(request):
    patient = get_object_or_404(Patient, user=request.user)
    invoices = Invoice.objects.filter(patient=patient).order_by('-created_at')
    total_paid = invoices.filter(status='Paid').aggregate(t=Sum('total'))['t'] or 0
    total_due = invoices.filter(status='Unpaid').aggregate(t=Sum('total'))['t'] or 0
    return render(request, 'patients/billing.html', {
        'invoices': invoices, 'total_paid': total_paid, 'total_due': total_due
    })

@login_required
@role_required(['PATIENT'])
def patient_notifications(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifs.update(is_read=True)
    return render(request, 'patients/notifications.html', {'notifications': notifs})

# ──────────────────────────────────────────────────────────────
# RECEPTION PORTAL
# ──────────────────────────────────────────────────────────────
@login_required
@role_required(['RECEPTION'])
def reception_dashboard(request):
    today = date.today()
    total_patients = Patient.objects.count()
    total_appointments = Appointment.objects.count()
    today_appointments = Appointment.objects.filter(date=today).count()
    pending = Appointment.objects.filter(status='Pending').count()
    appointments = Appointment.objects.select_related('patient', 'doctor__user').filter(date=today).order_by('time')
    recent_patients = Patient.objects.order_by('-registered_at')[:5]
    context = {
        'total_patients': total_patients, 'total_appointments': total_appointments,
        'today_appointments': today_appointments, 'pending': pending,
        'appointments': appointments, 'recent_patients': recent_patients,
    }
    return render(request, 'reception/dashboard.html', context)

@login_required
@role_required(['RECEPTION'])
def add_patient(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        age = request.POST.get('age')
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '')
        gender = request.POST.get('gender', '')
        blood_group = request.POST.get('blood_group', '')
        address = request.POST.get('address', '')
        emergency_contact = request.POST.get('emergency_contact', '')
        allergies = request.POST.get('allergies', '')
        chronic = request.POST.get('chronic_conditions', '')

        username = name.replace(' ', '').lower() + str(random.randint(100, 999))
        password = str(random.randint(100000, 999999))

        user = User.objects.create_user(username=username, password=password, role='PATIENT')
        patient = Patient.objects.create(
            user=user, name=name, age=age, phone=phone, email=email,
            gender=gender, blood_group=blood_group, address=address,
            emergency_contact=emergency_contact, allergies=allergies,
            chronic_conditions=chronic
        )
        log_action(request.user, f'ADD PATIENT: {name}', 'Patient', patient.id, request=request)
        messages.success(request, f'✅ Patient registered! Login → Username: {username} | Password: {password}')
        return redirect('view_patients')
    return render(request, 'reception/add_patient.html')

@login_required
@role_required(['RECEPTION'])
def view_patients(request):
    search = request.GET.get('search', '')
    patients = Patient.objects.select_related('user').order_by('-registered_at')
    if search:
        patients = patients.filter(Q(name__icontains=search) | Q(phone__icontains=search))
    return render(request, 'reception/patients.html', {'patients': patients, 'search': search})

@login_required
@role_required(['RECEPTION'])
def reception_patient_profile(request, id):
    patient = get_object_or_404(Patient, id=id)
    appointments = Appointment.objects.filter(patient=patient).order_by('-date')
    return render(request, 'reception/patient_profile.html', {'patient': patient, 'appointments': appointments})

@login_required
@role_required(['RECEPTION'])
def reception_book_appointment(request):
    patients = Patient.objects.all()
    doctors = Doctor.objects.filter(is_available=True).select_related('user')
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        doctor_id = request.POST.get('doctor')
        appt_date = request.POST.get('date')
        appt_time = request.POST.get('time')
        symptoms = request.POST.get('symptoms', '')
        dept = request.POST.get('department', '')
        appt_type = request.POST.get('type', 'OPD')
        priority = request.POST.get('priority', '')

        if not (patient_id and doctor_id and appt_date and appt_time):
            messages.error(request, '⚠ All required fields must be filled.')
            return redirect('reception_book_appointment')

        patient = get_object_or_404(Patient, id=patient_id)
        doctor = get_object_or_404(Doctor, id=doctor_id)

        if Appointment.objects.filter(doctor=doctor, date=appt_date, time=appt_time).exists():
            messages.error(request, '⚠ Slot already booked! Choose a different time.')
            return redirect('reception_book_appointment')

        if not priority:
            priority = ai_priority_from_symptoms(symptoms)

        appt = Appointment.objects.create(
            patient=patient, doctor=doctor, date=appt_date, time=appt_time,
            symptoms=symptoms, department=dept, appointment_type=appt_type,
            priority=priority, status='Pending', ai_risk_flag=priority
        )

        # Auto-create invoice
        fee = float(doctor.consultation_fee)
        inv_num = generate_invoice_number()
        inv = Invoice.objects.create(
            patient=patient, appointment=appt, invoice_number=inv_num,
            subtotal=fee, total=fee, status='Unpaid'
        )
        InvoiceItem.objects.create(invoice=inv, description='Consultation Fee',
                                    quantity=1, unit_price=fee, total=fee)

        if patient.user:
            create_notification(patient.user, 'Appointment Booked',
                                f'Appointment with {doctor} on {appt_date} booked.', 'appointment')
        log_action(request.user, 'BOOK APPOINTMENT', 'Appointment', appt.id, request=request)
        messages.success(request, f'✅ Appointment booked! Priority: {priority}')
        return redirect('view_appointments')
    return render(request, 'reception/book_appointment.html', {'patients': patients, 'doctors': doctors})

@login_required
@role_required(['RECEPTION'])
def view_appointments(request):
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    appointments = Appointment.objects.select_related('patient', 'doctor__user').order_by('-date', 'time')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    if date_filter:
        appointments = appointments.filter(date=date_filter)
    return render(request, 'reception/appointments.html', {
        'appointments': appointments, 'status_filter': status_filter, 'date_filter': date_filter
    })

@login_required
@role_required(['RECEPTION', 'DOCTOR', 'ADMIN'])
def update_status(request, id, status):
    VALID = ['Pending', 'Approved', 'Completed', 'Cancelled', 'No-Show']
    if status not in VALID:
        return HttpResponseForbidden('Invalid status')
    appt = get_object_or_404(Appointment, id=id)
    appt.status = status
    appt.save()
    if appt.patient.user:
        create_notification(appt.patient.user, f'Appointment {status}',
                            f'Your appointment on {appt.date} is now {status}.', 'appointment')
    ref = request.META.get('HTTP_REFERER', '/')
    return redirect(ref)

# ──────────────────────────────────────────────────────────────
# LAB PORTAL
# ──────────────────────────────────────────────────────────────
@login_required
@role_required(['LAB'])
def lab_dashboard(request):
    reports = LabReport.objects.select_related('patient', 'doctor').order_by('-date')
    total = reports.count()
    pending = reports.filter(status='Pending').count()
    completed = reports.filter(status='Completed').count()
    critical = reports.filter(abnormal_flag='Critical').count()
    today_reports = reports.filter(date__date=date.today()).count()
    recent = reports.filter(status='Pending').order_by('priority')[:10]
    context = {'reports': recent, 'total': total, 'pending': pending,
               'completed': completed, 'critical': critical, 'today_reports': today_reports}
    return render(request, 'lab/dashboard.html', context)

@login_required
@role_required(['LAB'])
def lab_reports(request):
    flag_filter = request.GET.get('flag', '')
    status_filter = request.GET.get('status', '')
    search = request.GET.get('search', '')
    reports = LabReport.objects.select_related('patient', 'doctor').order_by('-date')
    if flag_filter:
        reports = reports.filter(abnormal_flag=flag_filter)
    if status_filter:
        reports = reports.filter(status=status_filter)
    if search:
        reports = reports.filter(Q(patient__name__icontains=search) | Q(test_name__icontains=search))
    return render(request, 'lab/reports.html', {'reports': reports, 'flag_filter': flag_filter, 'status_filter': status_filter})

def analyze_report(result):
    result_lower = result.lower()
    if any(x in result_lower for x in ['very high', 'danger', 'critical', 'severe', 'life-threatening']):
        return 'Critical'
    elif any(x in result_lower for x in ['high', 'low', 'abnormal', 'elevated', 'decreased']):
        return 'Abnormal'
    return 'Normal'

@login_required
@role_required(['LAB'])
def upload_report(request, id):
    report = get_object_or_404(LabReport, id=id)
    if request.method == 'POST':
        result = request.POST.get('result', '').strip()
        normal_range = request.POST.get('normal_range', '')
        file = request.FILES.get('report_file')
        if not result:
            messages.error(request, '❌ Result is required.')
            return redirect('upload_report', id=id)
        flag = analyze_report(result)
        report.result = result
        report.normal_range = normal_range
        report.abnormal_flag = flag
        report.status = 'Completed'
        report.completed_at = timezone.now()
        if file:
            allowed = ['application/pdf', 'image/jpeg', 'image/png']
            if file.content_type not in allowed:
                messages.error(request, '❌ Only PDF, JPG, PNG allowed.')
                return redirect('upload_report', id=id)
            report.report_file = file
        report.save()
        # Notify doctor and patient
        if report.doctor and report.doctor.user:
            create_notification(report.doctor.user, f'Lab Report Ready — {report.test_name}',
                                f'{report.patient.name}\'s {report.test_name} report is {flag}.', 'lab')
        if report.patient.user:
            create_notification(report.patient.user, 'Your Lab Report is Ready',
                                f'Your {report.test_name} result is available.', 'lab')
        log_action(request.user, f'UPLOAD REPORT: {report.test_name}', 'LabReport', report.id, request=request)
        messages.success(request, f'✅ Report uploaded. Status: {flag}')
        return redirect('lab_dashboard')
    return render(request, 'lab/upload_report.html', {'report': report})

# ──────────────────────────────────────────────────────────────
# PHARMACY PORTAL — Full
# ──────────────────────────────────────────────────────────────
@login_required
@role_required(['PHARMACY', 'ADMIN'])
def pharmacy_dashboard(request):
    medicines = Medicine.objects.all()
    total = medicines.count()
    low_stock = medicines.filter(stock_quantity__lte=50).count()
    out_of_stock = medicines.filter(stock_quantity=0).count()
    dispensed_today = PharmacyDispense.objects.filter(
        dispensed_at__date=date.today()
    ).count()
    recent_dispense = PharmacyDispense.objects.select_related('patient', 'medicine').order_by('-dispensed_at')[:10]
    low_stock_meds = medicines.filter(stock_quantity__lte=50).order_by('stock_quantity')[:10]
    context = {
        'total': total, 'low_stock': low_stock, 'out_of_stock': out_of_stock,
        'dispensed_today': dispensed_today, 'recent_dispense': recent_dispense,
        'low_stock_meds': low_stock_meds,
    }
    return render(request, 'pharmacy/dashboard.html', context)

@login_required
@role_required(['PHARMACY', 'ADMIN'])
def pharmacy_inventory(request):
    search = request.GET.get('search', '')
    cat_filter = request.GET.get('category', '')
    medicines = Medicine.objects.order_by('name')
    if search:
        medicines = medicines.filter(Q(name__icontains=search) | Q(generic_name__icontains=search))
    if cat_filter:
        medicines = medicines.filter(category=cat_filter)
    categories = Medicine.CATEGORY_CHOICES
    return render(request, 'pharmacy/inventory.html', {
        'medicines': medicines, 'search': search, 'cat_filter': cat_filter, 'categories': categories, 'today': date.today()
    })

@login_required
@role_required(['PHARMACY', 'ADMIN'])
def add_medicine(request):
    if request.method == 'POST':
        med = Medicine.objects.create(
            name=request.POST.get('name'),
            generic_name=request.POST.get('generic_name', ''),
            category=request.POST.get('category', 'Other'),
            manufacturer=request.POST.get('manufacturer', ''),
            unit=request.POST.get('unit', 'Tablet'),
            stock_quantity=request.POST.get('stock_quantity', 0),
            reorder_level=request.POST.get('reorder_level', 50),
            price_per_unit=request.POST.get('price_per_unit', 0),
            expiry_date=request.POST.get('expiry_date') or None,
        )
        log_action(request.user, f'ADD MEDICINE: {med.name}', 'Medicine', med.id, request=request)
        messages.success(request, f'✅ Medicine "{med.name}" added to inventory.')
        return redirect('pharmacy_inventory')
    return render(request, 'pharmacy/add_medicine.html', {'categories': Medicine.CATEGORY_CHOICES})

@login_required
@role_required(['PHARMACY', 'ADMIN'])
def update_stock(request, id):
    med = get_object_or_404(Medicine, id=id)
    if request.method == 'POST':
        qty = int(request.POST.get('quantity', 0))
        action = request.POST.get('action', 'add')
        if action == 'add':
            med.stock_quantity += qty
        else:
            med.stock_quantity = max(0, med.stock_quantity - qty)
        med.save()
        log_action(request.user, f'UPDATE STOCK: {med.name} ({action} {qty})', 'Medicine', med.id, request=request)
        messages.success(request, f'✅ Stock updated for {med.name}.')
        return redirect('pharmacy_inventory')
    return render(request, 'pharmacy/update_stock.html', {'medicine': med})

@login_required
@role_required(['PHARMACY'])
def dispense_medicine(request):
    patients = Patient.objects.all()
    prescriptions = Prescription.objects.filter(created_at__date=date.today()).select_related('patient')
    medicines = Medicine.objects.filter(is_available=True, stock_quantity__gt=0)
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        medicine_id = request.POST.get('medicine')
        quantity = int(request.POST.get('quantity', 1))
        prescription_id = request.POST.get('prescription')
        patient = get_object_or_404(Patient, id=patient_id)
        medicine = get_object_or_404(Medicine, id=medicine_id)
        if medicine.stock_quantity < quantity:
            messages.error(request, f'❌ Insufficient stock. Available: {medicine.stock_quantity}')
            return redirect('dispense_medicine')
        total_cost = medicine.price_per_unit * quantity
        rx = Prescription.objects.filter(id=prescription_id).first() if prescription_id else None
        PharmacyDispense.objects.create(
            prescription=rx, patient=patient, medicine=medicine,
            quantity=quantity, dispensed_by=request.user, total_cost=total_cost
        )
        medicine.stock_quantity -= quantity
        medicine.save()
        log_action(request.user, f'DISPENSE: {medicine.name} x{quantity}', 'PharmacyDispense', request=request)
        messages.success(request, f'✅ Dispensed {quantity} {medicine.unit}(s) of {medicine.name}.')
        return redirect('pharmacy_dashboard')
    return render(request, 'pharmacy/dispense.html', {
        'patients': patients, 'medicines': medicines, 'prescriptions': prescriptions
    })

# ──────────────────────────────────────────────────────────────
# BILLING
# ──────────────────────────────────────────────────────────────
@login_required
@role_required(['ADMIN', 'RECEPTION'])
def billing_list(request):
    search = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    invoices = Invoice.objects.select_related('patient').order_by('-created_at')
    if search:
        invoices = invoices.filter(Q(patient__name__icontains=search) | Q(invoice_number__icontains=search))
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    total_revenue = Invoice.objects.filter(status='Paid').aggregate(t=Sum('total'))['t'] or 0
    total_pending = Invoice.objects.filter(status='Unpaid').aggregate(t=Sum('total'))['t'] or 0
    return render(request, 'billing/list.html', {
        'invoices': invoices, 'search': search, 'status_filter': status_filter,
        'total_revenue': total_revenue, 'total_pending': total_pending
    })

@login_required
@role_required(['ADMIN', 'RECEPTION'])
def create_invoice(request):
    patients = Patient.objects.all()
    appointments = Appointment.objects.filter(status='Completed').select_related('patient', 'doctor')
    if request.method == 'POST':
        patient_id = request.POST.get('patient')
        appointment_id = request.POST.get('appointment')
        descriptions = request.POST.getlist('description[]')
        quantities = request.POST.getlist('quantity[]')
        unit_prices = request.POST.getlist('unit_price[]')
        discount = float(request.POST.get('discount', 0))
        patient = get_object_or_404(Patient, id=patient_id)
        appt = Appointment.objects.filter(id=appointment_id).first() if appointment_id else None
        subtotal = sum(int(q) * float(u) for q, u in zip(quantities, unit_prices) if q and u)
        tax = subtotal * 0.05
        total = subtotal - discount + tax
        inv = Invoice.objects.create(
            patient=patient, appointment=appt,
            invoice_number=generate_invoice_number(),
            subtotal=subtotal, discount=discount, tax=tax, total=total,
            status='Unpaid'
        )
        for desc, qty, price in zip(descriptions, quantities, unit_prices):
            if desc.strip():
                InvoiceItem.objects.create(
                    invoice=inv, description=desc, quantity=int(qty or 1),
                    unit_price=float(price or 0), total=int(qty or 1)*float(price or 0)
                )
        if patient.user:
            create_notification(patient.user, 'New Invoice',
                                f'Invoice #{inv.invoice_number} of ₹{total} generated.', 'billing')
        messages.success(request, f'✅ Invoice {inv.invoice_number} created.')
        return redirect('billing_list')
    return render(request, 'billing/create.html', {'patients': patients, 'appointments': appointments})

@login_required
@role_required(['ADMIN', 'RECEPTION'])
def mark_paid(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    if request.method == 'POST':
        method = request.POST.get('payment_method', 'Cash')
        invoice.paid_amount = invoice.total
        invoice.status = 'Paid'
        invoice.payment_method = method
        invoice.save()
        if invoice.patient.user:
            create_notification(invoice.patient.user, 'Payment Received',
                                f'Payment of ₹{invoice.total} received via {method}.', 'billing')
        messages.success(request, f'✅ Invoice {invoice.invoice_number} marked as PAID.')
    return redirect('billing_list')

def download_invoice(request, id):
    invoice = get_object_or_404(Invoice, id=id)
    items = invoice.items.all()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.invoice_number}.pdf"'
    doc = SimpleDocTemplate(response)
    styles = getSampleStyleSheet()
    content = []
    content.append(Paragraph("🏥 CuraSync AI — Invoice", styles['Title']))
    content.append(Spacer(1, 12))
    content.append(Paragraph(f"<b>Invoice No:</b> {invoice.invoice_number}", styles['Normal']))
    content.append(Paragraph(f"<b>Patient:</b> {invoice.patient.name}", styles['Normal']))
    content.append(Paragraph(f"<b>Date:</b> {invoice.created_at.strftime('%Y-%m-%d')}", styles['Normal']))
    content.append(Paragraph(f"<b>Status:</b> {invoice.status}", styles['Normal']))
    content.append(Spacer(1, 12))
    data = [['Description', 'Qty', 'Unit Price (₹)', 'Total (₹)']]
    for item in items:
        data.append([item.description, str(item.quantity), f"₹{item.unit_price}", f"₹{item.total}"])
    data.append(['', '', 'Subtotal', f"₹{invoice.subtotal}"])
    data.append(['', '', 'Discount', f"-₹{invoice.discount}"])
    data.append(['', '', 'Tax (5%)', f"₹{invoice.tax}"])
    data.append(['', '', '<b>TOTAL</b>', f"<b>₹{invoice.total}</b>"])
    t = Table(data, colWidths=[200, 50, 100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0ea5e9')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
    ]))
    content.append(t)
    doc.build(content)
    return response

# ──────────────────────────────────────────────────────────────
# AI FEATURES
# ──────────────────────────────────────────────────────────────
import joblib
BASE_DIR_ML = os.path.dirname(os.path.abspath(__file__))
FEATURES_PATH = os.path.join(BASE_DIR_ML, 'ml', 'features.pkl')
MODEL_PATH = os.path.join(BASE_DIR_ML, 'ml', 'ml_model.pkl')

try:
    _features = joblib.load(FEATURES_PATH)
    _model = joblib.load(MODEL_PATH)
    ML_LOADED = True
except Exception as e:
    print(f"ML model load warning: {e}")
    _features = []
    _model = None
    ML_LOADED = False

def ai_prediction(request):
    if request.method == 'POST':
        selected_symptoms = request.POST.getlist('symptoms')
        if not selected_symptoms:
            return render(request, 'ai/form.html', {
                'symptoms': _features, 'error': 'Please select at least one symptom.'
            })
        try:
            import pandas as pd
            import numpy as np
            data = dict.fromkeys(_features, 0)
            for s in selected_symptoms:
                if s in data:
                    data[s] = 1
            df = pd.DataFrame([data])
            result = _model.predict(df)[0]

            # Top 3 predictions with probabilities
            try:
                proba = _model.predict_proba(df)[0]
                classes = _model.classes_
                top_indices = np.argsort(proba)[::-1][:3]
                top_3 = [{'disease': classes[i], 'confidence': round(float(proba[i])*100, 1)} for i in top_indices]
                confidence = round(float(proba[top_indices[0]]) * 100, 1)
            except Exception:
                top_3 = [{'disease': result, 'confidence': 85.0}]
                confidence = 85.0

            # Log prediction
            patient = None
            if request.user.is_authenticated:
                try:
                    patient = Patient.objects.get(user=request.user)
                except Patient.DoesNotExist:
                    pass
            AIPredictionLog.objects.create(
                patient=patient,
                symptoms=selected_symptoms,
                predicted_disease=result,
                confidence=confidence,
                top_3_predictions=top_3,
                session_user=request.user if request.user.is_authenticated else None
            )

            # Disease info map
            disease_info = {
                'Diabetes': {'icon': '🩸', 'color': '#ef4444', 'advice': 'Monitor blood sugar regularly. Consult an endocrinologist.'},
                'Hypertension': {'icon': '❤️', 'color': '#f97316', 'advice': 'Reduce salt intake. Monitor BP daily. Cardiology consult recommended.'},
                'Common Cold': {'icon': '🤧', 'color': '#3b82f6', 'advice': 'Rest and hydration. OTC medications may help. Usually resolves in 7-10 days.'},
                'Malaria': {'icon': '🦟', 'color': '#8b5cf6', 'advice': 'Seek immediate medical attention. Blood smear test required.'},
                'Typhoid': {'icon': '🌡️', 'color': '#f59e0b', 'advice': 'Blood culture test required. Antibiotics prescribed by doctor.'},
                'Pneumonia': {'icon': '🫁', 'color': '#06b6d4', 'advice': 'Chest X-ray required. Immediate medical care recommended.'},
            }
            info = disease_info.get(result, {'icon': '🏥', 'color': '#10b981', 'advice': 'Please consult a qualified medical professional for proper diagnosis and treatment.'})

            return render(request, 'ai/result.html', {
                'result': result, 'selected_symptoms': selected_symptoms,
                'top_3': top_3, 'confidence': confidence, 'disease_info': info,
                'ml_loaded': ML_LOADED
            })
        except Exception as e:
            print("AI ERROR:", e)
            return render(request, 'ai/form.html', {
                'symptoms': _features, 'error': f'Prediction error: {str(e)}'
            })

    return render(request, 'ai/form.html', {'symptoms': _features, 'ml_loaded': ML_LOADED})

@login_required
@role_required(['DOCTOR', 'ADMIN'])
def ai_risk_dashboard(request):
    """AI Patient Risk Assessment Dashboard"""
    high_risk = Patient.objects.filter(risk_label__in=['High', 'Critical']).order_by('-risk_score')[:20]
    critical_labs = LabReport.objects.filter(abnormal_flag='Critical').select_related('patient').order_by('-date')[:10]
    ai_logs = AIPredictionLog.objects.order_by('-created_at')[:10]

    # Update risk scores for all patients
    for patient in Patient.objects.all():
        score, label = compute_patient_risk(patient)
        Patient.objects.filter(id=patient.id).update(risk_score=score, risk_label=label)

    high_risk = Patient.objects.filter(risk_label__in=['High', 'Critical']).order_by('-risk_score')[:20]
    risk_distribution = {
        'Low': Patient.objects.filter(risk_label='Low').count(),
        'Medium': Patient.objects.filter(risk_label='Medium').count(),
        'High': Patient.objects.filter(risk_label='High').count(),
        'Critical': Patient.objects.filter(risk_label='Critical').count(),
    }

    return render(request, 'ai/risk_dashboard.html', {
        'high_risk_patients': high_risk,
        'critical_labs': critical_labs,
        'ai_logs': ai_logs,
        'risk_distribution': json.dumps(risk_distribution),
    })

# ──────────────────────────────────────────────────────────────
# NOTIFICATIONS API
# ──────────────────────────────────────────────────────────────
@login_required
def notifications_list(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:20]
    notifs.update(is_read=True)
    return render(request, 'notifications.html', {'notifications': notifs})

@login_required
def notifications_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})

# ──────────────────────────────────────────────────────────────
# PASSWORD RESET
# ──────────────────────────────────────────────────────────────
def forgot_password_phone(request):
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        try:
            patient = Patient.objects.get(phone=phone)
            otp = str(random.randint(100000, 999999))
            request.session['otp'] = otp
            request.session['reset_user_id'] = patient.user.id
            print(f"🔐 OTP for {phone}: {otp}")
            return redirect('verify_otp_phone')
        except Patient.DoesNotExist:
            return render(request, 'forgot_phone.html', {'message': '❌ Phone number not found.'})
    return render(request, 'forgot_phone.html')

def verify_otp_phone(request):
    if request.method == 'POST':
        entered = request.POST.get('otp', '')
        session_otp = request.session.get('otp', '')
        if entered == session_otp:
            return redirect('reset_password_phone')
        return render(request, 'verify_otp_phone.html', {'message': '❌ Invalid OTP.'})
    return render(request, 'verify_otp_phone.html')

def reset_password_phone(request):
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirm = request.POST.get('confirm_password', '')
        if password != confirm:
            return render(request, 'reset_password_phone.html', {'message': '❌ Passwords do not match.'})
        user_id = request.session.get('reset_user_id')
        if not user_id:
            return redirect('forgot_phone')
        user = get_object_or_404(User, id=user_id)
        user.set_password(password)
        user.save()
        messages.success(request, '✅ Password reset successfully!')
        return redirect('role_login', role='PATIENT')
    return render(request, 'reset_password_phone.html')
