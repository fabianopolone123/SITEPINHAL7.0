from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0067_loja_variacoes_multiplas_obrigatorias'),
    ]

    operations = [
        migrations.AddField(
            model_name='lojaprodutovariacao',
            name='orientacoes',
            field=models.TextField(blank=True, default='', verbose_name='orientações ao selecionar'),
        ),
    ]
