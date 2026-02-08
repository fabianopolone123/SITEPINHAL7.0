from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_whatsapp_confirmacao_notificacao'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(blank=True, max_length=150, verbose_name='username')),
                ('profile', models.CharField(blank=True, max_length=64, verbose_name='perfil')),
                ('location', models.CharField(blank=True, max_length=255, verbose_name='onde')),
                ('action', models.CharField(max_length=255, verbose_name='o que fez')),
                ('details', models.TextField(blank=True, verbose_name='detalhes')),
                ('method', models.CharField(blank=True, max_length=12, verbose_name='metodo')),
                ('path', models.CharField(blank=True, max_length=255, verbose_name='caminho')),
                ('ip_address', models.CharField(blank=True, max_length=64, verbose_name='ip')),
                ('user_agent', models.CharField(blank=True, max_length=255, verbose_name='user agent')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='data/hora')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'log de auditoria',
                'verbose_name_plural': 'logs de auditoria',
                'ordering': ('-created_at',),
            },
        ),
    ]
