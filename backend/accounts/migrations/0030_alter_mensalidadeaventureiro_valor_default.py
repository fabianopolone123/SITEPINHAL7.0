from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0029_lojaproduto_lojaprodutovariacao'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mensalidadeaventureiro',
            name='valor',
            field=models.DecimalField(decimal_places=2, default=Decimal('30.00'), max_digits=10, verbose_name='valor'),
        ),
    ]
