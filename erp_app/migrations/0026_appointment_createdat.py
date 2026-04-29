from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [('erp_app', '0025_upgrade_v2')]
    operations = [
        migrations.AddField(model_name='appointment', name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True)),
    ]
