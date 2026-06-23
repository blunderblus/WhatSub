from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_userpreferencechatsession_userpreferenceprofile_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='usertasteanalysis',
            unique_together=set(),
        ),
    ]
