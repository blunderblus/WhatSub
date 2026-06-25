from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('community', '0005_communitypost_platform'),
    ]

    operations = [
        migrations.AddField(
            model_name='communitypost',
            name='flair_tag',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]
