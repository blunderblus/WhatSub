# Generated manually for content reactions.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contents', '0003_content_watchmode_checked'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContentReaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reaction', models.CharField(choices=[('like', 'Like'), ('dislike', 'Dislike')], max_length=7)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='contents.content')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='content_reactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('content', 'user')},
            },
        ),
    ]
