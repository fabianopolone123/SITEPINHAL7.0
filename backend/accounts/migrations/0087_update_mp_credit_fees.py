from django.db import migrations
from decimal import Decimal

NEW_RATES = {
    'credit_2x_percent':  Decimal('5.98'),
    'credit_3x_percent':  Decimal('8.97'),
    'credit_4x_percent':  Decimal('11.96'),
    'credit_5x_percent':  Decimal('14.95'),
    'credit_6x_percent':  Decimal('17.94'),
    'credit_7x_percent':  Decimal('21.63'),
    'credit_8x_percent':  Decimal('24.72'),
    'credit_9x_percent':  Decimal('27.81'),
    'credit_10x_percent': Decimal('30.90'),
    'credit_11x_percent': Decimal('33.99'),
    'credit_12x_percent': Decimal('37.08'),
}


def update_rates(apps, schema_editor):
    MercadoPagoFeeConfig = apps.get_model('accounts', 'MercadoPagoFeeConfig')
    MercadoPagoFeeConfig.objects.all().update(**NEW_RATES)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0086_mercadopagofeeconfig_per_installment'),
    ]

    operations = [
        migrations.RunPython(update_rates, migrations.RunPython.noop),
    ]
