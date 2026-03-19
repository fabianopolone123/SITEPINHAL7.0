from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0053_evento_event_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='event_description',
            field=models.TextField(blank=True, verbose_name='descricao do evento'),
        ),
    ]

