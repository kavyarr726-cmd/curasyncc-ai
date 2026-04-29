"""
Management command: python manage.py seed_data
Creates demo users, departments, patients, doctors, medicines, wards, beds, appointments
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
import random

from erp_app.models import (
    User, Patient, Doctor, Department, Appointment, Prescription,
    PrescriptionItem, LabReport, Ward, Bed, Medicine, Invoice, InvoiceItem
)


class Command(BaseCommand):
    help = 'Seeds the database with demo data for CuraSync AI v2'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🌱 Seeding CuraSync AI v2 database...'))

        # ── Superuser / Admin ──
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@curasyncai.com', 'admin123', role='ADMIN',
                                           first_name='System', last_name='Admin')
            self.stdout.write('  ✅ Admin: admin / admin123')

        # ── Departments ──
        depts = {}
        for name in ['Cardiology', 'Neurology', 'Orthopedics', 'Pediatrics', 'General Medicine',
                     'Gynecology', 'Dermatology', 'ENT', 'Oncology', 'Psychiatry']:
            d, _ = Department.objects.get_or_create(name=name, defaults={'description': f'{name} department'})
            depts[name] = d

        # ── Doctors ──
        doctor_data = [
            ('drpatel', 'Rajesh', 'Patel', 'Cardiology', 15, 'MBBS, MD Cardiology', 800),
            ('drsharma', 'Priya', 'Sharma', 'Neurology', 12, 'MBBS, DM Neurology', 900),
            ('drgupta', 'Amit', 'Gupta', 'Orthopedics', 10, 'MBBS, MS Ortho', 700),
            ('drkhan', 'Fatima', 'Khan', 'Pediatrics', 8, 'MBBS, MD Pediatrics', 600),
            ('drreddy', 'Suresh', 'Reddy', 'General Medicine', 20, 'MBBS, MD', 500),
            ('drsingh', 'Meena', 'Singh', 'Gynecology', 14, 'MBBS, MS Gynae', 750),
        ]
        doctors = []
        for uname, fn, ln, spec, exp, qual, fee in doctor_data:
            if not User.objects.filter(username=uname).exists():
                u = User.objects.create_user(uname, f'{uname}@curasyncai.com', 'doctor123',
                                              role='DOCTOR', first_name=fn, last_name=ln)
                doc = Doctor.objects.create(user=u, specialization=spec, department=depts.get(spec),
                                             experience_years=exp, qualification=qual, phone='9800000000',
                                             consultation_fee=fee, rating=round(random.uniform(3.8, 5.0), 1))
                doctors.append(doc)
        if not doctors:
            doctors = list(Doctor.objects.all())
        self.stdout.write(f'  ✅ {len(doctors)} Doctors created')

        # ── Reception ──
        if not User.objects.filter(username='reception').exists():
            User.objects.create_user('reception', 'reception@curasyncai.com', 'reception123',
                                      role='RECEPTION', first_name='Sunita', last_name='Verma')
            self.stdout.write('  ✅ Receptionist: reception / reception123')

        # ── Lab Tech ──
        if not User.objects.filter(username='labtech').exists():
            User.objects.create_user('labtech', 'lab@curasyncai.com', 'lab123',
                                      role='LAB', first_name='Ravi', last_name='Kumar')
            self.stdout.write('  ✅ Lab Tech: labtech / lab123')

        # ── Pharmacist ──
        if not User.objects.filter(username='pharmacy').exists():
            User.objects.create_user('pharmacy', 'pharmacy@curasyncai.com', 'pharmacy123',
                                      role='PHARMACY', first_name='Anita', last_name='Shah')
            self.stdout.write('  ✅ Pharmacist: pharmacy / pharmacy123')

        # ── Patients ──
        patient_data = [
            ('patient1', 'Arun', 'Kumar', 45, '9876543210', 'M', 'A+'),
            ('patient2', 'Sunita', 'Devi', 38, '9876543211', 'F', 'B+'),
            ('patient3', 'Mohan', 'Das', 62, '9876543212', 'M', 'O+'),
            ('patient4', 'Priya', 'Nair', 29, '9876543213', 'F', 'AB-'),
            ('patient5', 'Ramesh', 'Yadav', 55, '9876543214', 'M', 'B-'),
        ]
        patients = []
        for uname, fn, ln, age, phone, gender, bg in patient_data:
            if not User.objects.filter(username=uname).exists():
                u = User.objects.create_user(uname, f'{uname}@mail.com', 'patient123',
                                              role='PATIENT', first_name=fn, last_name=ln)
                p = Patient.objects.create(user=u, name=f'{fn} {ln}', age=age, phone=phone,
                                            gender=gender, blood_group=bg,
                                            chronic_conditions=random.choice(['', 'Diabetes', 'Hypertension', 'Asthma', '']))
                patients.append(p)
        if not patients:
            patients = list(Patient.objects.all())
        self.stdout.write(f'  ✅ {len(patients)} Patients created')

        # ── Appointments ──
        statuses = ['Pending', 'Approved', 'Completed', 'Cancelled']
        types = ['OPD', 'IPD', 'Follow-up', 'Emergency']
        priorities = ['Normal', 'High', 'Emergency', 'Low']
        appt_count = 0
        for i in range(15):
            p = random.choice(patients)
            d = random.choice(doctors)
            appt_date = date.today() + timedelta(days=random.randint(-10, 10))
            if not Appointment.objects.filter(patient=p, doctor=d, date=appt_date).exists():
                Appointment.objects.create(
                    patient=p, doctor=d, date=appt_date,
                    time=f'{random.randint(9,16):02d}:{random.choice(["00","30"])} {"AM" if random.randint(9,16)<12 else "PM"}',
                    status=random.choice(statuses),
                    appointment_type=random.choice(types),
                    priority=random.choice(priorities),
                    symptoms=random.choice(['Fever and headache', 'Chest pain', 'Back pain', 'Cough and cold', 'Joint pain'])
                )
                appt_count += 1
        self.stdout.write(f'  ✅ {appt_count} Appointments created')

        # ── Lab Reports ──
        tests = ['CBC', 'Blood Sugar Fasting', 'Lipid Profile', 'LFT', 'KFT', 'Thyroid Profile', 'HbA1c', 'Urine Routine']
        flags = ['Normal', 'Abnormal', 'Critical']
        for i in range(12):
            p = random.choice(patients)
            LabReport.objects.create(
                patient=p, doctor=random.choice(doctors),
                test_name=random.choice(tests),
                result=random.choice(['Within normal limits', 'Slightly elevated', 'High — immediate attention required']),
                abnormal_flag=random.choice(flags),
                status=random.choice(['Pending', 'Completed']),
                priority=random.choice(['Normal', 'High'])
            )
        self.stdout.write('  ✅ 12 Lab Reports created')

        # ── Wards & Beds ──
        ward_data = [('General Ward A', 'General', 1, 20), ('ICU', 'ICU', 2, 10),
                     ('Private Ward', 'Private', 3, 15), ('Emergency Ward', 'Emergency', 0, 8)]
        for wname, wtype, floor, beds in ward_data:
            ward, created = Ward.objects.get_or_create(name=wname, defaults={'ward_type': wtype, 'floor': floor, 'total_beds': beds})
            if created:
                for i in range(1, beds + 1):
                    occupied = random.random() < 0.4
                    b = Bed.objects.create(ward=ward, bed_number=f'{wname[0]}{i:02d}', is_occupied=occupied)
                    if occupied and patients:
                        b.patient = random.choice(patients)
                        b.admitted_at = timezone.now() - timedelta(days=random.randint(1, 5))
                        b.save()
        self.stdout.write('  ✅ Wards & Beds created')

        # ── Medicines ──
        med_data = [
            ('Paracetamol 500mg', 'Acetaminophen', 'Analgesic', 500, 5.0),
            ('Amoxicillin 250mg', 'Amoxicillin', 'Antibiotic', 200, 12.0),
            ('Metformin 500mg', 'Metformin HCl', 'Diabetes', 150, 8.0),
            ('Atorvastatin 10mg', 'Atorvastatin', 'Cardiovascular', 300, 15.0),
            ('Azithromycin 500mg', 'Azithromycin', 'Antibiotic', 40, 45.0),
            ('ORS Sachets', 'ORS', 'Other', 600, 3.0),
            ('Vitamin C 500mg', 'Ascorbic Acid', 'Vitamins', 20, 10.0),
            ('Omeprazole 20mg', 'Omeprazole', 'Other', 250, 6.0),
            ('Cetirizine 10mg', 'Cetirizine', 'Other', 180, 4.0),
            ('Pantoprazole 40mg', 'Pantoprazole', 'Other', 300, 9.0),
        ]
        for name, generic, cat, qty, price in med_data:
            Medicine.objects.get_or_create(name=name, defaults={
                'generic_name': generic, 'category': cat,
                'stock_quantity': qty, 'price_per_unit': price,
                'reorder_level': 50, 'manufacturer': 'Generic Pharma'
            })
        self.stdout.write('  ✅ 10 Medicines added to inventory')

        # ── Invoices ──
        for p in patients[:3]:
            inv_num = f'INV{date.today().strftime("%Y%m%d")}{random.randint(1000,9999)}'
            if not Invoice.objects.filter(invoice_number=inv_num).exists():
                total = random.randint(500, 5000)
                inv = Invoice.objects.create(
                    patient=p, invoice_number=inv_num,
                    subtotal=total, tax=total * 0.05, total=total * 1.05,
                    status=random.choice(['Paid', 'Unpaid']),
                    payment_method=random.choice(['Cash', 'UPI', 'Card'])
                )
                InvoiceItem.objects.create(
                    invoice=inv, description='Consultation + Tests',
                    quantity=1, unit_price=total, total=total
                )
        self.stdout.write('  ✅ Sample Invoices created')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🎉 Seeding complete! Login credentials:'))
        self.stdout.write('  👑 Admin:      admin / admin123')
        self.stdout.write('  👨‍⚕️ Doctors:    drpatel, drsharma, drgupta / doctor123')
        self.stdout.write('  🗂️  Reception:  reception / reception123')
        self.stdout.write('  🧪 Lab Tech:   labtech / lab123')
        self.stdout.write('  💊 Pharmacy:   pharmacy / pharmacy123')
        self.stdout.write('  🏥 Patients:   patient1–patient5 / patient123')
