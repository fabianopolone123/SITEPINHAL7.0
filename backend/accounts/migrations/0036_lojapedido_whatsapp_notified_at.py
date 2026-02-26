from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0035_loja_pedido_e_itens'),
    ]

    operations = [
        migrations.AddField(
            model_name='lojapedido',
            name='whatsapp_notified_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='whatsapp notificado em'),
        ),
    ]
