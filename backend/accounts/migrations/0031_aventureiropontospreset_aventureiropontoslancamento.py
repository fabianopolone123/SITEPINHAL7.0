from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0030_alter_mensalidadeaventureiro_valor_default'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AventureiroPontosPreset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=160, verbose_name='nome')),
                ('pontos', models.IntegerField(verbose_name='pontos')),
                ('motivo_padrao', models.CharField(max_length=255, verbose_name='motivo padrão')),
                ('ativo', models.BooleanField(default=True, verbose_name='ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pontos_presets_criados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'pré-registro de pontos',
                'verbose_name_plural': 'pré-registros de pontos',
                'ordering': ('nome',),
            },
        ),
        migrations.CreateModel(
            name='AventureiroPontosLancamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pontos', models.IntegerField(verbose_name='pontos')),
                ('motivo', models.CharField(max_length=255, verbose_name='motivo')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('aventureiro', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pontos_lancamentos', to='accounts.aventureiro')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pontos_lancados', to=settings.AUTH_USER_MODEL)),
                ('preset', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lancamentos', to='accounts.aventureiropontospreset')),
            ],
            options={
                'verbose_name': 'lançamento de pontos do aventureiro',
                'verbose_name_plural': 'lançamentos de pontos dos aventureiros',
                'ordering': ('-created_at',),
            },
        ),
    ]

