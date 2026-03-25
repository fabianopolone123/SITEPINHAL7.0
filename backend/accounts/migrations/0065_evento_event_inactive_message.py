from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0064_evento_pagina_ativa'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='event_inactive_message',
            field=models.TextField(blank=True, verbose_name='mensagem da pagina inativa'),
        ),
    ]
