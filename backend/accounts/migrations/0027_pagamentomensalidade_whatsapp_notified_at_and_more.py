from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0026_pagamentomensalidade'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagamentomensalidade',
            name='whatsapp_notified_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='whatsapp notificado em'),
        ),
        migrations.AlterField(
            model_name='whatsapptemplate',
            name='notification_type',
            field=models.CharField(choices=[('cadastro', 'Cadastro'), ('diretoria', 'Diretoria'), ('confirmacao', 'Confirmação'), ('financeiro', 'Financeiro'), ('teste', 'Teste')], max_length=32, unique=True, verbose_name='tipo de notificacao'),
        ),
    ]
