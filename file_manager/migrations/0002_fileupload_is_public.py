from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('file_manager', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileupload',
            name='is_public',
            field=models.BooleanField(default=False, verbose_name='Public File'),
        ),
    ]