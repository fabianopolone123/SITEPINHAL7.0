from django.db import migrations, models
from decimal import Decimal


def set_band_rates(apps, schema_editor):
    MercadoPagoFeeConfig = apps.get_model('accounts', 'MercadoPagoFeeConfig')
    MercadoPagoFeeConfig.objects.all().update(
        credit_per_parcel_2_6x=Decimal('2.99'),
        credit_per_parcel_7_12x=Decimal('3.09'),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0087_update_mp_credit_fees'),
    ]

    operations = [
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_per_parcel_2_6x',
            field=models.DecimalField(
                'crédito 2x–6x (% por parcela)',
                max_digits=5,
                decimal_places=2,
                default=Decimal('2.99'),
            ),
        ),
        migrations.AddField(
            model_name='mercadopagofeeconfig',
            name='credit_per_parcel_7_12x',
            field=models.DecimalField(
                'crédito 7x–12x (% por parcela)',
                max_digits=5,
                decimal_places=2,
                default=Decimal('3.09'),
            ),
        ),
        migrations.RunPython(set_band_rates, migrations.RunPython.noop),
    ]
