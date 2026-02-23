from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0025_mensalidadeaventureiro_valor'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PagamentoMensalidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor_total', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor total')),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('processando', 'Processando'), ('pago', 'Pago'), ('cancelado', 'Cancelado'), ('falha', 'Falha')], default='pendente', max_length=16, verbose_name='status')),
                ('mp_payment_id', models.CharField(blank=True, max_length=64, verbose_name='MP payment id')),
                ('mp_external_reference', models.CharField(blank=True, max_length=128, verbose_name='MP external reference')),
                ('mp_status', models.CharField(blank=True, max_length=32, verbose_name='MP status')),
                ('mp_status_detail', models.CharField(blank=True, max_length=128, verbose_name='MP status detail')),
                ('mp_qr_code', models.TextField(blank=True, verbose_name='MP QR code Pix')),
                ('mp_qr_code_base64', models.TextField(blank=True, verbose_name='MP QR code base64')),
                ('paid_at', models.DateTimeField(blank=True, null=True, verbose_name='pago em')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pagamentos_mensalidade_criados', to=settings.AUTH_USER_MODEL)),
                ('responsavel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pagamentos_mensalidade', to='accounts.responsavel')),
            ],
            options={
                'verbose_name': 'pagamento de mensalidades',
                'verbose_name_plural': 'pagamentos de mensalidades',
                'ordering': ('-created_at',),
            },
        ),
        migrations.AddField(
            model_name='pagamentomensalidade',
            name='mensalidades',
            field=models.ManyToManyField(blank=True, related_name='pagamentos', to='accounts.mensalidadeaventureiro'),
        ),
    ]
