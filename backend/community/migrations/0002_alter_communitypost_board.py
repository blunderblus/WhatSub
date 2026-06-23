from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='communitypost',
            name='board',
            field=models.CharField(choices=[('notice', 'Notice'), ('ott', 'OTT'), ('free', 'Free')], db_index=True, max_length=10),
        ),
    ]
