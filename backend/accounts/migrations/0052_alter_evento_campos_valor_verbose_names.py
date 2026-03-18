from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0051_evento_inscricao_valor_config_and_faixa_idade'),
    ]

    operations = [
        migrations.AlterField(
            model_name='evento',
            name='inscricao_valor_unitario',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=10,
                verbose_name='valor unitário da inscrição',
            ),
        ),
        migrations.AlterField(
            model_name='eventoinscricao',
            name='valor_inscricao',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=10,
                verbose_name='valor da inscrição',
            ),
        ),
        migrations.AlterField(
            model_name='eventoinscricao',
            name='valor_inscricao_unidades',
            field=models.PositiveIntegerField(
                default=0,
                verbose_name='unidades da cobrança de inscrição',
            ),
        ),
    ]
