from django.db import migrations, models
import django.db.models.deletion
import accounts.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0047_eventoinscricao_codigo_inscricao_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EventoCusto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255, verbose_name='nome do custo')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor')),
                ('comprovante', models.FileField(blank=True, null=True, upload_to=accounts.models.evento_custo_comprovante_upload_to, verbose_name='comprovante')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eventos_custos_cadastrados', to=settings.AUTH_USER_MODEL)),
                ('evento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custos', to='accounts.evento')),
            ],
            options={
                'verbose_name': 'custo de evento',
                'verbose_name_plural': 'custos de eventos',
                'ordering': ('-created_at',),
            },
        ),
    ]
