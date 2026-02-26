from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0034_lojaproduto_minimo_pedidos_pagos'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LojaPedido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('forma_pagamento', models.CharField(choices=[('pix', 'Pix')], default='pix', max_length=24, verbose_name='forma de pagamento')),
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
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pedidos_loja_criados', to=settings.AUTH_USER_MODEL)),
                ('responsavel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pedidos_loja', to='accounts.responsavel')),
            ],
            options={
                'verbose_name': 'pedido da loja',
                'verbose_name_plural': 'pedidos da loja',
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='LojaPedidoItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('produto_titulo', models.CharField(max_length=255, verbose_name='produto (snapshot)')),
                ('variacao_nome', models.CharField(max_length=255, verbose_name='variação (snapshot)')),
                ('quantidade', models.PositiveIntegerField(verbose_name='quantidade')),
                ('valor_unitario', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor unitário')),
                ('valor_total', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor total')),
                ('foto_url', models.TextField(blank=True, verbose_name='foto URL (snapshot)')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='accounts.lojapedido')),
                ('produto', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_pedido', to='accounts.lojaproduto')),
                ('variacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='itens_pedido', to='accounts.lojaprodutovariacao')),
            ],
            options={
                'verbose_name': 'item do pedido da loja',
                'verbose_name_plural': 'itens dos pedidos da loja',
                'ordering': ('pedido_id', 'id'),
            },
        ),
    ]
