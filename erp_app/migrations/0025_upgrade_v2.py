from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('erp_app', '0024_labreport_abnormal_flag'),
    ]

    operations = [
        # User - new fields
        migrations.AddField(model_name='user', name='phone',
            field=models.CharField(blank=True, max_length=15, null=True)),
        migrations.AddField(model_name='user', name='profile_pic',
            field=models.ImageField(blank=True, null=True, upload_to='profiles/')),

        # Patient - new fields (user_id and basic fields already exist)
        migrations.AddField(model_name='patient', name='risk_score',
            field=models.FloatField(default=0.0)),
        migrations.AddField(model_name='patient', name='risk_label',
            field=models.CharField(default='Low', max_length=20)),
        migrations.AddField(model_name='patient', name='gender',
            field=models.CharField(blank=True, choices=[('M','Male'),('F','Female'),('O','Other')], max_length=1, null=True)),
        migrations.AddField(model_name='patient', name='blood_group',
            field=models.CharField(blank=True, max_length=5, null=True)),
        migrations.AddField(model_name='patient', name='email',
            field=models.EmailField(blank=True, null=True)),
        migrations.AddField(model_name='patient', name='emergency_contact',
            field=models.CharField(blank=True, max_length=15, null=True)),
        migrations.AddField(model_name='patient', name='allergies',
            field=models.TextField(blank=True, null=True)),
        migrations.AddField(model_name='patient', name='chronic_conditions',
            field=models.TextField(blank=True, null=True)),
        migrations.AddField(model_name='patient', name='address',
            field=models.TextField(blank=True, null=True)),
        migrations.AddField(model_name='patient', name='registered_at',
            field=models.DateTimeField(auto_now_add=True, null=True)),

        # Doctor - new fields
        migrations.AddField(model_name='doctor', name='experience_years',
            field=models.IntegerField(default=0)),
        migrations.AddField(model_name='doctor', name='qualification',
            field=models.CharField(blank=True, max_length=200, null=True)),
        migrations.AddField(model_name='doctor', name='consultation_fee',
            field=models.DecimalField(decimal_places=2, default=500.0, max_digits=8)),
        migrations.AddField(model_name='doctor', name='available_days',
            field=models.CharField(default='Mon-Sat', max_length=100)),
        migrations.AddField(model_name='doctor', name='rating',
            field=models.FloatField(default=4.0)),
        migrations.AddField(model_name='doctor', name='is_available',
            field=models.BooleanField(default=True)),

        # Appointment - new fields (appointment_type, priority, time, department, symptoms already exist)
        migrations.AddField(model_name='appointment', name='ai_risk_flag',
            field=models.CharField(default='Normal', max_length=20)),
        migrations.AddField(model_name='appointment', name='notes',
            field=models.TextField(blank=True, null=True)),

        # Prescription - patient already exists, add new fields
        migrations.AddField(model_name='prescription', name='diagnosis',
            field=models.TextField(blank=True, null=True)),
        migrations.AddField(model_name='prescription', name='notes',
            field=models.TextField(blank=True, null=True)),
        migrations.AddField(model_name='prescription', name='follow_up_date',
            field=models.DateField(blank=True, null=True)),

        # PrescriptionItem
        migrations.AddField(model_name='prescriptionitem', name='frequency',
            field=models.CharField(default='Once daily', max_length=50)),
        migrations.AddField(model_name='prescriptionitem', name='instructions',
            field=models.CharField(blank=True, max_length=200, null=True)),

        # LabReport
        migrations.AddField(model_name='labreport', name='normal_range',
            field=models.CharField(blank=True, max_length=100, null=True)),
        migrations.AddField(model_name='labreport', name='priority',
            field=models.CharField(default='Normal', max_length=20)),
        migrations.AddField(model_name='labreport', name='completed_at',
            field=models.DateTimeField(blank=True, null=True)),

        # NEW MODELS
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Ward',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('ward_type', models.CharField(choices=[('General','General'),('ICU','ICU'),('Private','Private'),('Emergency','Emergency')], default='General', max_length=20)),
                ('floor', models.IntegerField(default=1)),
                ('total_beds', models.IntegerField(default=10)),
            ],
        ),
        migrations.CreateModel(
            name='Bed',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('bed_number', models.CharField(max_length=10)),
                ('is_occupied', models.BooleanField(default=False)),
                ('admitted_at', models.DateTimeField(blank=True, null=True)),
                ('patient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='erp_app.patient')),
                ('ward', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='erp_app.ward')),
            ],
        ),
        migrations.CreateModel(
            name='PatientVitals',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('blood_pressure_systolic', models.IntegerField(blank=True, null=True)),
                ('blood_pressure_diastolic', models.IntegerField(blank=True, null=True)),
                ('heart_rate', models.IntegerField(blank=True, null=True)),
                ('temperature', models.FloatField(blank=True, null=True)),
                ('oxygen_saturation', models.FloatField(blank=True, null=True)),
                ('weight', models.FloatField(blank=True, null=True)),
                ('height', models.FloatField(blank=True, null=True)),
                ('blood_sugar', models.FloatField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vitals', to='erp_app.patient')),
                ('recorded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='erp_app.user')),
            ],
            options={'ordering': ['-recorded_at']},
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('invoice_number', models.CharField(max_length=20, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('due_date', models.DateField(blank=True, null=True)),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('tax', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('paid_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('Unpaid','Unpaid'),('Paid','Paid'),('Partial','Partial'),('Waived','Waived')], default='Unpaid', max_length=10)),
                ('payment_method', models.CharField(blank=True, choices=[('Cash','Cash'),('Card','Card'),('UPI','UPI'),('Insurance','Insurance')], max_length=20, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='erp_app.patient')),
                ('appointment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='erp_app.appointment')),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('description', models.CharField(max_length=200)),
                ('quantity', models.IntegerField(default=1)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=8)),
                ('total', models.DecimalField(decimal_places=2, max_digits=8)),
                ('invoice', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='erp_app.invoice')),
            ],
        ),
        migrations.CreateModel(
            name='Medicine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('generic_name', models.CharField(blank=True, max_length=100, null=True)),
                ('category', models.CharField(choices=[('Antibiotic','Antibiotic'),('Analgesic','Analgesic'),('Antiviral','Antiviral'),('Antifungal','Antifungal'),('Cardiovascular','Cardiovascular'),('Diabetes','Diabetes'),('Vitamins','Vitamins'),('Other','Other')], default='Other', max_length=30)),
                ('manufacturer', models.CharField(blank=True, max_length=100, null=True)),
                ('unit', models.CharField(default='Tablet', max_length=20)),
                ('stock_quantity', models.IntegerField(default=0)),
                ('reorder_level', models.IntegerField(default=50)),
                ('price_per_unit', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('expiry_date', models.DateField(blank=True, null=True)),
                ('is_available', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='PharmacyDispense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('quantity', models.IntegerField(default=1)),
                ('total_cost', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('dispensed_at', models.DateTimeField(auto_now_add=True)),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='erp_app.medicine')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='erp_app.patient')),
                ('prescription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='erp_app.prescription')),
                ('dispensed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='erp_app.user')),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('notif_type', models.CharField(choices=[('appointment','Appointment'),('lab','Lab Report'),('billing','Billing'),('alert','Alert'),('system','System')], default='system', max_length=20)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('link', models.CharField(blank=True, max_length=200, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='erp_app.user')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AIPredictionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('symptoms', models.JSONField(default=list)),
                ('predicted_disease', models.CharField(max_length=200)),
                ('confidence', models.FloatField(default=0.0)),
                ('top_3_predictions', models.JSONField(default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('patient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='erp_app.patient')),
                ('session_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ai_predictions', to='erp_app.user')),
            ],
        ),
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('action', models.CharField(max_length=200)),
                ('model_name', models.CharField(blank=True, max_length=100, null=True)),
                ('object_id', models.IntegerField(blank=True, null=True)),
                ('details', models.TextField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='erp_app.user')),
            ],
            options={'ordering': ['-timestamp']},
        ),
        migrations.AddField(
            model_name='doctor',
            name='department',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='erp_app.department'),
        ),
        migrations.AddField(
            model_name='department',
            name='head_doctor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='headed_department', to='erp_app.doctor'),
        ),
    ]
# This file is complete - the created_at for appointment needs a separate migration
