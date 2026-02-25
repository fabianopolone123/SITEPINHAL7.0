from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0032_lojaprodutofoto'),
    ]

    operations = [
        migrations.AddField(
            model_name='lojaprodutofoto',
            name='todas_variacoes',
            field=models.BooleanField(default=False, verbose_name='todas as variações'),
        ),
        migrations.AddField(
            model_name='lojaprodutofoto',
            name='variacoes_vinculadas',
            field=models.ManyToManyField(blank=True, related_name='fotos_vinculadas_loja', to='accounts.lojaprodutovariacao'),
        ),
    ]
