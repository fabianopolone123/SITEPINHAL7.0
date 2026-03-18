from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0049_alter_eventoinscricao_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='inscricao_valor_modo',
            field=models.CharField(
                choices=[
                    ('nenhum', 'Sem cobranca de inscricao'),
                    ('fixo_inscricao', 'Valor fixo por inscricao'),
                    ('por_campo_preenchido', 'Valor por campo preenchido'),
                    ('por_item_repetidor', 'Valor por item de botao repetidor'),
                ],
                default='nenhum',
                max_length=32,
                verbose_name='modo de cobranca da inscricao',
            ),
        ),
        migrations.AddField(
            model_name='evento',
            name='inscricao_valor_unitario',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=10,
                verbose_name='valor unitario da inscricao',
            ),
        ),
        migrations.AddField(
            model_name='eventoinscricao',
            name='valor_inscricao',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                max_digits=10,
                verbose_name='valor da inscricao',
            ),
        ),
        migrations.AddField(
            model_name='eventoinscricao',
            name='valor_inscricao_unidades',
            field=models.PositiveIntegerField(
                default=0,
                verbose_name='unidades da cobranca de inscricao',
            ),
        ),
    ]