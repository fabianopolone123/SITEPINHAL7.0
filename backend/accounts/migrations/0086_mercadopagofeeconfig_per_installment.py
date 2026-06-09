from django.db import migrations, models
from decimal import Decimal

DEFAULTS = {
    'credit_2x_percent':  Decimal('9.90'),
    'credit_3x_percent':  Decimal('11.28'),
    'credit_4x_percent':  Decimal('12.64'),
    'credit_5x_percent':  Decimal('13.97'),
    'credit_6x_percent':  Decimal('15.27'),
    'credit_7x_percent':  Decimal('16.55'),
    'credit_8x_percent':  Decimal('17.81'),
    'credit_9x_percent':  Decimal('19.04'),
    'credit_10x_percent': Decimal('20.24'),
    'credit_11x_percent': Decimal('21.43'),
    'credit_12x_percent': Decimal('22.59'),
}


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0085_alter_cashback_fields_verbose_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_2x_percent',
            field=models.DecimalField('taxa crédito 2x (%)', max_digits=5, decimal_places=2, default=Decimal('9.90')),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_3x_percent',
            field=models.DecimalField('taxa crédito 3x (%)', max_digits=5, decimal_places=2, default=Decimal('11.28')),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_4x_percent',
            field=models.DecimalField('taxa crédito 4x (%)', max_digits=5, decimal_places=2, default=Decimal('12.64')),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_5x_percent',
            field=models.DecimalField('taxa crédito 5x (%)', max_digits=5, decimal_places=2, default=Decimal('13.97')),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_6x_percent',
            field=models.DecimalField('taxa crédito 6x (%)', max_digits=5, decimal_places=2, default=Decimal('15.27')),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_7x_percent',
            field=models.DecimalField('taxa crédito 7x (%)', max_digits=5, decimal_places=2, default=Decimal('16.55')),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_8x_percent',
            field=models.DecimalField('taxa crédito 8x (%)', max_digits=5, decimal_places=2, default=Decimal('17.81')),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_9x_percent',
            field=models.DecimalField('taxa crédito 9x (%)', max_digits=5, decimal_places=2, default=Decimal('19.04')),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_10x_percent',
            field=models.DecimalField('taxa crédito 10x (%)', max_digits=5, decimal_places=2, default=Decimal('20.24')),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_11x_percent',
            field=models.DecimalField('taxa crédito 11x (%)', max_digits=5, decimal_places=2, default=Decimal('21.43')),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_12x_percent',
            field=models.DecimalField('taxa crédito 12x (%)', max_digits=5, decimal_places=2, default=Decimal('22.59')),
        ),
    ]
