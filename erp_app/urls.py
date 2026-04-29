from django.urls import path
from . import views

urlpatterns = [
    # ── Home & Auth ──
    path('', views.home, name='home'),
    path('login/<str:role>/', views.login_view, name='role_login'),
    path('login/', views.login_view, {'role': 'PATIENT'}, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('redirect-dashboard/', views.redirect_dashboard, name='redirect_dashboard'),

    # ── Admin ──
    path('admin-portal/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-portal/users/', views.admin_users, name='admin_users'),
    path('admin-portal/users/create/', views.admin_create_user, name='admin_create_user'),
    path('admin-portal/users/<int:user_id>/toggle/', views.admin_toggle_user, name='admin_toggle_user'),
    path('admin-portal/departments/', views.admin_departments, name='admin_departments'),
    path('admin-portal/reports/', views.admin_reports, name='admin_reports'),
    path('admin-portal/wards/', views.admin_ward_management, name='admin_ward_management'),

    # ── Doctor ──
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/appointments/', views.doctor_appointments, name='doctor_appointments'),
    path('doctor/appointments/<int:id>/status/<str:status>/', views.update_appointment_status, name='update_appointment_status'),
    path('doctor/patients/', views.doctor_patients, name='doctor_patients'),
    path('doctor/prescriptions/', views.doctor_prescriptions, name='doctor_prescriptions'),
    path('doctor/reports/', views.doctor_reports, name='doctor_reports'),
    path('doctor/assign-lab-test/', views.assign_lab_test, name='assign_lab_test'),
    path('doctor/ai-risk/', views.ai_risk_dashboard, name='ai_risk_dashboard'),

    # ── Patient Profile ──
    path('patient/<int:id>/', views.patient_profile, name='patient_profile'),
    path('prescription/add/<int:id>/', views.add_prescription, name='add_prescription'),
    path('prescriptions/<int:id>/', views.view_prescriptions, name='view_prescriptions'),
    path('prescription/<int:id>/', views.prescription_detail, name='prescription_detail'),
    path('prescription/<int:id>/download/', views.download_prescription, name='download_prescription'),

    # ── Patient Portal ──
    path('patient-portal/', views.patient_dashboard, name='patient_dashboard'),
    path('patient-portal/book/', views.patient_book_appointment, name='patient_book_appointment'),
    path('patient-portal/appointments/', views.patient_appointments, name='patient_appointments'),
    path('patient-portal/prescriptions/', views.patient_prescriptions, name='patient_prescriptions'),
    path('patient-portal/reports/', views.patient_reports, name='patient_reports'),
    path('patient-portal/billing/', views.patient_billing, name='patient_billing'),
    path('patient-portal/notifications/', views.patient_notifications, name='patient_notifications'),

    # ── Reception ──
    path('reception/', views.reception_dashboard, name='reception_dashboard'),
    path('reception/patients/', views.view_patients, name='view_patients'),
    path('reception/patients/add/', views.add_patient, name='add_patient'),
    path('reception/patients/<int:id>/', views.reception_patient_profile, name='reception_patient_profile'),
    path('reception/book/', views.reception_book_appointment, name='reception_book_appointment'),
    path('reception/appointments/', views.view_appointments, name='view_appointments'),
    path('reception/appointments/<int:id>/status/<str:status>/', views.update_status, name='update_status'),

    # ── Lab ──
    path('lab/', views.lab_dashboard, name='lab_dashboard'),
    path('lab/reports/', views.lab_reports, name='lab_reports'),
    path('lab/upload/<int:id>/', views.upload_report, name='upload_report'),

    # ── Pharmacy ──
    path('pharmacy/', views.pharmacy_dashboard, name='pharmacy_dashboard'),
    path('pharmacy/inventory/', views.pharmacy_inventory, name='pharmacy_inventory'),
    path('pharmacy/inventory/add/', views.add_medicine, name='add_medicine'),
    path('pharmacy/inventory/<int:id>/stock/', views.update_stock, name='update_stock'),
    path('pharmacy/dispense/', views.dispense_medicine, name='dispense_medicine'),

    # ── Billing ──
    path('billing/', views.billing_list, name='billing_list'),
    path('billing/create/', views.create_invoice, name='create_invoice'),
    path('billing/<int:id>/pay/', views.mark_paid, name='mark_paid'),
    path('billing/<int:id>/download/', views.download_invoice, name='download_invoice'),

    # ── AI ──
    path('ai/predict/', views.ai_prediction, name='ai_prediction'),

    # ── Notifications ──
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('api/notifications/count/', views.notifications_count, name='notifications_count'),

    # ── Password Reset ──
    path('forgot-phone/', views.forgot_password_phone, name='forgot_phone'),
    path('verify-otp/', views.verify_otp_phone, name='verify_otp_phone'),
    path('reset-password/', views.reset_password_phone, name='reset_password_phone'),
]
