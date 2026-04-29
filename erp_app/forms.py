from django import forms
from .models import Patient, Doctor, Appointment, Prescription, PrescriptionItem, LabReport, Medicine

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['name', 'age', 'phone', 'email', 'gender', 'blood_group',
                  'address', 'emergency_contact', 'allergies', 'chronic_conditions']

class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'date', 'time', 'symptoms',
                  'appointment_type', 'priority', 'department']

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['patient', 'diagnosis', 'notes', 'follow_up_date']

class PrescriptionItemForm(forms.ModelForm):
    class Meta:
        model = PrescriptionItem
        fields = ['medicine', 'dosage', 'frequency', 'days', 'instructions']

class LabReportForm(forms.ModelForm):
    class Meta:
        model = LabReport
        fields = ['patient', 'test_name', 'result', 'normal_range', 'report_file', 'priority']

class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = ['name', 'generic_name', 'category', 'manufacturer', 'unit',
                  'stock_quantity', 'reorder_level', 'price_per_unit', 'expiry_date']
