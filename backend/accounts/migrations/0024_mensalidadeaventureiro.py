from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_alter_whatsapppreference_notify_confirmacao'),
    ]

    operations = [
        migrations.CreateModel(
            name='MensalidadeAventureiro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ano_referencia', models.PositiveIntegerField(verbose_name='ano de referência')),
                ('mes_referencia', models.PositiveSmallIntegerField(verbose_name='mês de referência')),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('paga', 'Paga')], default='pendente', max_length=16, verbose_name='status')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('aventureiro', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensalidades', to='accounts.aventureiro')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mensalidades_criadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'mensalidade do aventureiro',
                'verbose_name_plural': 'mensalidades dos aventureiros',
                'ordering': ('aventureiro__nome', 'ano_referencia', 'mes_referencia'),
                'unique_together': {('aventureiro', 'ano_referencia', 'mes_referencia')},
            },
        ),
    ]
