from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0027_pagamentomensalidade_whatsapp_notified_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='mensalidadeaventureiro',
            name='tipo',
            field=models.CharField(choices=[('inscricao', 'Inscrição'), ('mensalidade', 'Mensalidade')], default='mensalidade', max_length=16, verbose_name='tipo'),
        ),
    ]
