from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0036_lojapedido_whatsapp_notified_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='lojapedido',
            name='entregue',
            field=models.BooleanField(default=False, verbose_name='entregue'),
        ),
    ]
