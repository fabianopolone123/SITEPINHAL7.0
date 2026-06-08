from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0083_mercadopagofeeconfig'),
    ]

    operations = [
        # Campos cashback em PagamentoMensalidade
        migrations.AddField(
            model_name='pagamentomensalidade',
            name='cashback_aventureiro',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pagamentos_mensalidade_cashback',
                to='accounts.aventureiro',
                verbose_name='aventureiro cashback',
            ),
        ),
        migrations.AddField(
            model_name='pagamentomensalidade',
            name='cashback_desconto_valor',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=10,
                verbose_name='desconto cashback',
            ),
        ),
        # FK pagamento_mensalidade em AventureiroCashbackLancamento
        migrations.AddField(
            model_name='aventureirocashbacklancamento',
            name='pagamento_mensalidade',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cashback_lancamentos',
                to='accounts.pagamentomensalidade',
                verbose_name='pagamento mensalidade',
            ),
        ),
    ]
