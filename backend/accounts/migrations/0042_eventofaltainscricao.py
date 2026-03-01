from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import accounts.models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0041_pagamentomensalidade_entregue_guard'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventoFaltaInscricao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255, verbose_name='nome informado')),
                ('foto', models.ImageField(upload_to=accounts.models.presenca_falta_inscricao_upload_to, verbose_name='foto')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='faltas_inscricao_cadastradas', to=settings.AUTH_USER_MODEL)),
                ('evento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='faltas_inscricao', to='accounts.evento')),
            ],
            options={
                'verbose_name': 'falta de inscrição em evento',
                'verbose_name_plural': 'faltas de inscrição em eventos',
                'ordering': ('-created_at',),
            },
        ),
    ]
