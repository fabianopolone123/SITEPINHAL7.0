from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0066_mensalidade_cobranca_whatsapp_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='lojaproduto',
            name='permite_multiplas_variacoes',
            field=models.BooleanField(default=False, verbose_name='permite selecionar mais de uma variação'),
        ),
        migrations.AddField(
            model_name='lojaprodutovariacao',
            name='obrigatoria_compra',
            field=models.BooleanField(default=False, verbose_name='obrigatória na compra'),
        ),
        migrations.AddField(
            model_name='lojaprodutovariacao',
            name='obrigatoria_visual',
            field=models.BooleanField(default=False, verbose_name='obrigatória apenas visual'),
        ),
    ]
