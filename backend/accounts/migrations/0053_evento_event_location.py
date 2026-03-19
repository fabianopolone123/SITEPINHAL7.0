from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0052_alter_evento_campos_valor_verbose_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='event_location',
            field=models.CharField(blank=True, max_length=255, verbose_name='local do evento'),
        ),
    ]

