from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0038_apostilarequisito'),
    ]

    operations = [
        migrations.AddField(
            model_name='apostilarequisito',
            name='dicas',
            field=models.TextField(blank=True, verbose_name='dicas'),
        ),
        migrations.CreateModel(
            name='ApostilaSubRequisito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_subrequisito', models.CharField(max_length=32, verbose_name='código do subrequisito')),
                ('descricao', models.TextField(verbose_name='descrição')),
                ('resposta', models.TextField(blank=True, verbose_name='resposta')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='apostila_subrequisitos_criados', to=settings.AUTH_USER_MODEL)),
                ('requisito', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subrequisitos', to='accounts.apostilarequisito')),
            ],
            options={
                'verbose_name': 'subrequisito da apostila',
                'verbose_name_plural': 'subrequisitos da apostila',
                'ordering': ('requisito_id', 'codigo_subrequisito', 'id'),
                'unique_together': {('requisito', 'codigo_subrequisito')},
            },
        ),
    ]
