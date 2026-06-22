# Re-create CustomPlatformSubmission after 0004 removed it.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('subscriptions', '0004_delete_customplatformsubmission'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomPlatformSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('platform_name', models.CharField(max_length=100)),
                ('plan_name', models.CharField(blank=True, default='', max_length=100)),
                ('payment_amount', models.PositiveIntegerField()),
                ('billing_cycle', models.CharField(choices=[('weekly', 'Weekly'), ('monthly', 'Monthly'), ('annual', 'Annual')], max_length=10)),
                ('renewal_date', models.DateField(blank=True, null=True)),
                ('memo', models.TextField(blank=True, default='')),
                ('source', models.CharField(choices=[('gmail_onboarding', 'Gmail onboarding'), ('manual_onboarding', 'Manual onboarding')], default='gmail_onboarding', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_platform_submissions', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
