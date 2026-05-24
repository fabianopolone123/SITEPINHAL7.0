from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0080_eventoatendente'),
    ]

    operations = [
        migrations.AddField(
            model_name='lojapedido',
            name='transacao_teste',
            field=models.BooleanField(default=False, verbose_name='transacao de teste'),
        ),
    ]

