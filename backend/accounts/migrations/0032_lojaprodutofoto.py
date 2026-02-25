from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0031_aventureiropontospreset_aventureiropontoslancamento'),
    ]

    operations = [
        migrations.CreateModel(
            name='LojaProdutoFoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('foto', models.ImageField(upload_to='loja/produtos', verbose_name='foto')),
                ('ordem', models.PositiveIntegerField(default=0, verbose_name='ordem')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fotos', to='accounts.lojaproduto')),
                ('variacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fotos', to='accounts.lojaprodutovariacao')),
            ],
            options={
                'verbose_name': 'foto de produto',
                'verbose_name_plural': 'fotos de produto',
                'ordering': ('produto__titulo', 'ordem', 'id'),
            },
        ),
    ]
