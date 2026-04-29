# 🏥 CuraSync AI v2 — AI-Powered Hospital Management System

## 🚀 What's New vs Standard Hospital ERPs

| Feature | Standard ERPs | CuraSync AI v2 |
|---------|--------------|------------------|
| Disease Prediction | ❌ | ✅ Random Forest ML (top-3 + confidence %) |
| Patient Risk Scoring | ❌ | ✅ Auto ML-based risk stratification |
| Smart Appointment Priority | ❌ | ✅ NLP symptom analysis → auto-priority |
| Lab Anomaly Detection | ❌ | ✅ Auto Normal/Abnormal/Critical flagging |
| Vitals Trend Charts | ❌ | ✅ Interactive Chart.js dashboards |
| AI Prediction Audit Log | ❌ | ✅ Full transparency log per prediction |
| Ward/Bed Management | Basic | ✅ Real-time occupancy + admission/discharge |
| Pharmacy Inventory | Basic | ✅ Stock alerts, dispensing, expiry tracking |
| Billing/Invoicing | Basic | ✅ PDF invoices, multi-payment, tax calc |
| Notification System | ❌ | ✅ Real-time role-based notifications |
| Admin Portal | ❌ | ✅ Full RBAC user management + audit trail |
| PDF Downloads | ❌ | ✅ Prescriptions + invoices as PDF |

---

## 📋 Steps to Run

### 1. Install Python & pip (Python 3.10+)
```bash
python --version   # Should be 3.10 or higher
```

### 2. Create Virtual Environment
```bash
cd hospital_erp_v2
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Apply Database Migrations
```bash
python manage.py migrate
```

### 5. Seed Demo Data (Recommended)
```bash
python manage.py seed_data
```
This creates all demo users, departments, patients, doctors, medicines, wards, beds, appointments, and invoices.

### 6. (Optional) Train / Retrain ML Model
```bash
cd erp_app/ml
python train_model.py
cd ../..
```

### 7. Run the Server
```bash
python manage.py runserver
```

### 8. Open Browser
```
http://127.0.0.1:8000/
```

---

## 🔑 Login Credentials (after seed_data)

| Role | Username | Password | Portal |
|------|----------|----------|--------|
| 👑 Admin | `admin` | `admin123` | /admin-portal/ |
| 👨‍⚕️ Doctor | `drpatel` | `doctor123` | /doctor/ |
| 👨‍⚕️ Doctor | `drsharma` | `doctor123` | /doctor/ |
| 🗂️ Reception | `reception` | `reception123` | /reception/ |
| 🧪 Lab Tech | `labtech` | `lab123` | /lab/ |
| 💊 Pharmacy | `pharmacy` | `pharmacy123` | /pharmacy/ |
| 🏥 Patient | `patient1` | `patient123` | /patient-portal/ |
| 🏥 Patient | `patient2` | `patient123` | /patient-portal/ |

**Django Admin Panel:** http://127.0.0.1:8000/django-admin/ (admin / admin123)

---

## 🤖 AI/ML Features

### 1. Disease Prediction
- URL: `/ai/predict/`
- Model: Random Forest Classifier
- Output: Primary diagnosis + Top-3 predictions with confidence %
- All predictions logged in AIPredictionLog table

### 2. Patient Risk Scoring
- Automatically computed on every patient profile view
- Factors: age, vitals, chronic conditions, appointment history
- Labels: Low / Medium / High / Critical

### 3. Smart Appointment Priority
- NLP keyword matching on symptom text
- Auto-assigns: Emergency / High / Normal / Low
- Used at booking (both patient & reception portals)

### 4. Lab Report Anomaly Detection
- Keyword analysis on result text
- Auto-flags: Normal / Abnormal / Critical
- Triggers notifications to doctor and patient

### 5. Vitals Trend Analysis
- Chart.js line charts on patient profile
- Tracks: BP, Heart Rate, SpO2, Temperature
- Visible to doctors on patient profile page

### 6. AI Risk Dashboard
- URL: `/doctor/ai-risk/`
- Shows all high-risk patients ranked by score
- Displays critical lab reports and recent AI predictions

---

## 🏗️ Project Structure

```
hospital_erp_v2/
├── manage.py
├── requirements.txt
├── README.md
├── db.sqlite3
├── hosp_erp2/
│   ├── settings.py
│   └── urls.py
└── erp_app/
    ├── models.py          # 15 models
    ├── views.py           # 50+ views
    ├── urls.py            # 50+ URL routes
    ├── admin.py           # Full Django admin
    ├── forms.py
    ├── apps.py
    ├── ml/
    │   ├── ml_model.pkl   # Trained RF model
    │   ├── features.pkl   # Feature list
    │   └── train_model.py
    ├── migrations/
    │   └── 0025_upgrade_v2.py
    ├── management/
    │   └── commands/
    │       └── seed_data.py
    └── templates/
        ├── base.html
        ├── home.html
        ├── login.html
        ├── admin/       (5 templates)
        ├── dashboards/  (admin dashboard)
        ├── doctors/     (8 templates)
        ├── patients/    (7 templates)
        ├── reception/   (6 templates)
        ├── lab/         (3 templates)
        ├── pharmacy/    (5 templates)
        ├── billing/     (2 templates)
        └── ai/          (3 templates)
```
