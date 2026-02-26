from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0039_apostilasubrequisito_apostilarequisito_dicas'),
    ]

    operations = [
        migrations.AddField(
            model_name='apostilarequisito',
            name='foto_requisito',
            field=models.ImageField(blank=True, null=True, upload_to='apostila/requisitos', verbose_name='foto do requisito'),
        ),
        migrations.CreateModel(
            name='ApostilaDica',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto', models.TextField(verbose_name='texto da dica')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='apostila_dicas_criadas', to=settings.AUTH_USER_MODEL)),
                ('requisito', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dicas_rows', to='accounts.apostilarequisito')),
            ],
            options={
                'verbose_name': 'dica da apostila',
                'verbose_name_plural': 'dicas da apostila',
                'ordering': ('requisito_id', 'id'),
            },
        ),
        migrations.CreateModel(
            name='ApostilaDicaArquivo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('arquivo', models.FileField(upload_to='apostila/dicas/arquivos', verbose_name='arquivo da dica')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('dica', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='arquivos', to='accounts.apostiladica')),
            ],
            options={
                'verbose_name': 'arquivo da dica da apostila',
                'verbose_name_plural': 'arquivos das dicas da apostila',
                'ordering': ('dica_id', 'id'),
            },
        ),
    ]
