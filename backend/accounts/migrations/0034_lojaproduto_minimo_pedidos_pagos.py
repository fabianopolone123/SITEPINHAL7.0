from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0033_lojaprodutofoto_todas_variacoes_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='lojaproduto',
            name='minimo_pedidos_pagos',
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                verbose_name='mínimo de pedidos pagos para produção',
            ),
        ),
    ]
