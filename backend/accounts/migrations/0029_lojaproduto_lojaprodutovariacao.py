from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0028_mensalidadeaventureiro_tipo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LojaProduto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255, verbose_name='título')),
                ('descricao', models.TextField(blank=True, verbose_name='descrição')),
                ('foto', models.ImageField(blank=True, null=True, upload_to='loja/produtos', verbose_name='foto')),
                ('ativo', models.BooleanField(default=True, verbose_name='ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='loja_produtos_criados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'produto da loja',
                'verbose_name_plural': 'produtos da loja',
                'ordering': ('-created_at',),
            },
        ),
        migrations.CreateModel(
            name='LojaProdutoVariacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255, verbose_name='variação')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor')),
                ('estoque', models.IntegerField(blank=True, null=True, verbose_name='estoque')),
                ('ativo', models.BooleanField(default=True, verbose_name='ativo')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variacoes', to='accounts.lojaproduto')),
            ],
            options={
                'verbose_name': 'variação de produto',
                'verbose_name_plural': 'variações de produto',
                'ordering': ('produto__titulo', 'nome'),
            },
        ),
    ]
