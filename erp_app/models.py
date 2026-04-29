from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'), ('DOCTOR', 'Doctor'), ('RECEPTION', 'Reception'),
        ('LAB', 'Lab Technician'), ('PHARMACY', 'Pharmacist'), ('PATIENT', 'Patient'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='PATIENT')
    profile_pic = models.ImageField(upload_to='profiles/', null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class Department(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    head_doctor = models.ForeignKey('Doctor', on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_department')

    def __str__(self):
        return self.name


class Patient(models.Model):
    BLOOD_GROUP_CHOICES = [
        ('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-'),
    ]
    GENDER_CHOICES = [('M','Male'),('F','Female'),('O','Other')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    phone = models.CharField(max_length=15)
    email = models.EmailField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=15, null=True, blank=True)
    allergies = models.TextField(null=True, blank=True)
    chronic_conditions = models.TextField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    risk_score = models.FloatField(default=0.0)
    risk_label = models.CharField(max_length=20, default='Low')

    def __str__(self):
        return self.name


class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    specialization = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    experience_years = models.IntegerField(default=0)
    qualification = models.CharField(max_length=200, null=True, blank=True)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=500.00)
    available_days = models.CharField(max_length=100, default='Mon-Sat')
    rating = models.FloatField(default=4.0)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"Dr. {self.user.get_full_name() if self.user else 'Unknown'}"


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('Pending','Pending'),('Approved','Approved'),('Completed','Completed'),('Cancelled','Cancelled'),('No-Show','No-Show'),
    ]
    PRIORITY_CHOICES = [('Emergency','Emergency'),('High','High'),('Normal','Normal'),('Low','Low')]
    TYPE_CHOICES = [('OPD','OPD'),('IPD','IPD'),('Emergency','Emergency'),('Follow-up','Follow-up'),('Teleconsult','Teleconsult')]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateField()
    time = models.CharField(max_length=20, null=True, blank=True)
    symptoms = models.TextField(null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    appointment_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='OPD')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    notes = models.TextField(null=True, blank=True)
    ai_risk_flag = models.CharField(max_length=20, default='Normal')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.name} → {self.doctor} ({self.date})"


class Prescription(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)
    diagnosis = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rx #{self.id} — {self.patient.name if self.patient else 'Unknown'}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    medicine = models.CharField(max_length=100)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=50, default='Once daily')
    days = models.IntegerField(null=True, blank=True)
    instructions = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.medicine


class LabReport(models.Model):
    STATUS_CHOICES = [('Pending','Pending'),('In Progress','In Progress'),('Completed','Completed')]
    FLAG_CHOICES = [('Normal','Normal'),('Abnormal','Abnormal'),('Critical','Critical')]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True)
    test_name = models.CharField(max_length=100)
    result = models.TextField(blank=True)
    normal_range = models.CharField(max_length=100, null=True, blank=True)
    report_file = models.FileField(upload_to='lab_reports/', null=True, blank=True)
    abnormal_flag = models.CharField(max_length=20, choices=FLAG_CHOICES, default='Normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    priority = models.CharField(max_length=20, default='Normal')
    date = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.patient.name} — {self.test_name}"


class Ward(models.Model):
    WARD_TYPES = [('General','General'),('ICU','ICU'),('Private','Private'),('Emergency','Emergency')]
    name = models.CharField(max_length=100)
    ward_type = models.CharField(max_length=20, choices=WARD_TYPES, default='General')
    floor = models.IntegerField(default=1)
    total_beds = models.IntegerField(default=10)

    def available_beds(self):
        return self.bed_set.filter(is_occupied=False).count()

    def __str__(self):
        return f"{self.name} ({self.ward_type})"


class Bed(models.Model):
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE)
    bed_number = models.CharField(max_length=10)
    is_occupied = models.BooleanField(default=False)
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    admitted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Bed {self.bed_number} — {self.ward.name}"


class PatientVitals(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='vitals')
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    oxygen_saturation = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    blood_sugar = models.FloatField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-recorded_at']

    def bmi(self):
        if self.weight and self.height and self.height > 0:
            return round(self.weight / ((self.height / 100) ** 2), 1)
        return None

    def __str__(self):
        return f"Vitals — {self.patient.name}"


class Invoice(models.Model):
    STATUS_CHOICES = [('Unpaid','Unpaid'),('Paid','Paid'),('Partial','Partial'),('Waived','Waived')]
    PAYMENT_METHODS = [('Cash','Cash'),('Card','Card'),('UPI','UPI'),('Insurance','Insurance')]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    invoice_number = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def balance(self):
        return float(self.total) - float(self.paid_amount)

    def __str__(self):
        return f"INV-{self.invoice_number} | {self.patient.name}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    description = models.CharField(max_length=200)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=8, decimal_places=2)


class Medicine(models.Model):
    CATEGORY_CHOICES = [
        ('Antibiotic','Antibiotic'),('Analgesic','Analgesic'),('Antiviral','Antiviral'),
        ('Antifungal','Antifungal'),('Cardiovascular','Cardiovascular'),('Diabetes','Diabetes'),
        ('Vitamins','Vitamins'),('Other','Other'),
    ]
    name = models.CharField(max_length=100)
    generic_name = models.CharField(max_length=100, null=True, blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='Other')
    manufacturer = models.CharField(max_length=100, null=True, blank=True)
    unit = models.CharField(max_length=20, default='Tablet')
    stock_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=50)
    price_per_unit = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    expiry_date = models.DateField(null=True, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_low_stock(self):
        return self.stock_quantity <= self.reorder_level

    def __str__(self):
        return f"{self.name} ({self.stock_quantity} {self.unit}s)"


class PharmacyDispense(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, null=True, blank=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    dispensed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    dispensed_at = models.DateTimeField(auto_now_add=True)
    total_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)


class Notification(models.Model):
    TYPE_CHOICES = [
        ('appointment','Appointment'),('lab','Lab Report'),
        ('billing','Billing'),('alert','Alert'),('system','System'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class AIPredictionLog(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    symptoms = models.JSONField(default=list)
    predicted_disease = models.CharField(max_length=200)
    confidence = models.FloatField(default=0.0)
    top_3_predictions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    session_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"AI: {self.predicted_disease}"


class Receptionist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=15)
    shift = models.CharField(max_length=20, default='Morning')

    def __str__(self):
        return self.user.username if self.user else 'Unknown'


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=200)
    model_name = models.CharField(max_length=100, null=True, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
