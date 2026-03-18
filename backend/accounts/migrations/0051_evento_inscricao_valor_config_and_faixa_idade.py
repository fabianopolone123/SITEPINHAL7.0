from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0050_evento_valor_inscricao_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='inscricao_valor_config',
            field=models.JSONField(blank=True, default=dict, verbose_name='configuracao da cobranca da inscricao'),
        ),
        migrations.AlterField(
            model_name='evento',
            name='inscricao_valor_modo',
            field=models.CharField(
                choices=[
                    ('nenhum', 'Sem cobrança de inscrição'),
                    ('fixo_inscricao', 'Valor fixo por inscrição'),
                    ('por_campo_preenchido', 'Valor por campo preenchido'),
                    ('por_item_repetidor', 'Valor por item de botão repetidor'),
                    ('faixa_idade_repetidor', 'Valor por faixa de idade (botão repetidor)'),
                ],
                default='nenhum',
                max_length=32,
                verbose_name='modo de cobrança da inscrição',
            ),
        ),
    ]
