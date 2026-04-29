from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (User, Patient, Doctor, Department, Appointment,
                     Prescription, PrescriptionItem, LabReport, Ward, Bed,
                     PatientVitals, Invoice, InvoiceItem, Medicine,
                     PharmacyDispense, Notification, AIPredictionLog,
                     Receptionist, AuditLog)

admin.site.site_header = "🏥 CuraSync AI — Admin Portal"
admin.site.site_title = "CuraSync AI Admin"
admin.site.index_title = "AI Hospital Management System"


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    fieldsets = UserAdmin.fieldsets + (
        ("Role & Profile", {"fields": ("role", "phone", "profile_pic")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Role Information", {"fields": ("role", "phone")}),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'head_doctor', 'description')
    search_fields = ('name',)


class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'gender', 'blood_group', 'phone', 'risk_label', 'registered_at')
    list_filter = ('gender', 'blood_group', 'risk_label')
    search_fields = ('name', 'phone', 'email')
    readonly_fields = ('registered_at', 'risk_score', 'risk_label')


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'department', 'experience_years', 'consultation_fee', 'is_available')
    list_filter = ('specialization', 'department', 'is_available')
    search_fields = ('user__first_name', 'user__last_name', 'specialization')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'date', 'time', 'status', 'priority', 'appointment_type')
    list_filter = ('status', 'priority', 'appointment_type', 'date')
    search_fields = ('patient__name', 'doctor__user__first_name')
    date_hierarchy = 'date'


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'diagnosis', 'created_at', 'follow_up_date')
    inlines = [PrescriptionItemInline]
    search_fields = ('patient__name', 'doctor__user__first_name')
    list_filter = ('created_at',)


@admin.register(LabReport)
class LabReportAdmin(admin.ModelAdmin):
    list_display = ('patient', 'test_name', 'status', 'abnormal_flag', 'priority', 'date')
    list_filter = ('status', 'abnormal_flag', 'priority')
    search_fields = ('patient__name', 'test_name')


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ('name', 'ward_type', 'floor', 'total_beds', 'available_beds')

@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ('bed_number', 'ward', 'is_occupied', 'patient', 'admitted_at')
    list_filter = ('is_occupied', 'ward')


@admin.register(PatientVitals)
class PatientVitalsAdmin(admin.ModelAdmin):
    list_display = ('patient', 'heart_rate', 'blood_pressure_systolic', 'temperature', 'oxygen_saturation', 'recorded_at')
    list_filter = ('recorded_at',)
    search_fields = ('patient__name',)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'patient', 'total', 'paid_amount', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('invoice_number', 'patient__name')
    inlines = [InvoiceItemInline]


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'stock_quantity', 'reorder_level', 'price_per_unit', 'expiry_date', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name', 'generic_name')


@admin.register(PharmacyDispense)
class PharmacyDispenseAdmin(admin.ModelAdmin):
    list_display = ('patient', 'medicine', 'quantity', 'total_cost', 'dispensed_by', 'dispensed_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notif_type', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read')


@admin.register(AIPredictionLog)
class AIPredictionLogAdmin(admin.ModelAdmin):
    list_display = ('patient', 'predicted_disease', 'confidence', 'created_at')
    list_filter = ('predicted_disease',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'model_name', 'object_id', 'timestamp', 'ip_address')
    list_filter = ('model_name',)
    readonly_fields = ('timestamp',)

admin.site.register(Receptionist)
