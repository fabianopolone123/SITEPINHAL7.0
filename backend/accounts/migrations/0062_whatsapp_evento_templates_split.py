from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0061_financeirocomprovante'),
    ]

    operations = [
        migrations.AlterField(
            model_name='whatsappqueue',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('cadastro', 'Cadastro'),
                    ('diretoria', 'Diretoria'),
                    ('confirmacao', 'Confirmação'),
                    ('financeiro', 'Financeiro'),
                    ('loja', 'Loja'),
                    ('evento_inscricao', 'Nova inscricao de evento'),
                    ('evento_inscricao_responsavel', 'Confirmacao de evento (inscrito)'),
                    ('evento_inscricao_diretoria', 'Confirmacao de evento (diretoria)'),
                    ('geral', 'Geral'),
                    ('teste', 'Teste'),
                    ('indicacao_codigo', 'Codigo de indicacao'),
                ],
                default='geral',
                max_length=32,
                verbose_name='tipo notificacao',
            ),
        ),
        migrations.AlterField(
            model_name='whatsapptemplate',
            name='notification_type',
            field=models.CharField(
                choices=[
                    ('cadastro', 'Cadastro'),
                    ('diretoria', 'Diretoria'),
                    ('confirmacao', 'Confirmação'),
                    ('financeiro', 'Financeiro'),
                    ('loja', 'Loja'),
                    ('evento_inscricao', 'Nova inscricao de evento'),
                    ('evento_inscricao_responsavel', 'Confirmacao de evento (inscrito)'),
                    ('evento_inscricao_diretoria', 'Confirmacao de evento (diretoria)'),
                    ('teste', 'Teste'),
                    ('indicacao_codigo', 'Codigo de indicacao'),
                ],
                max_length=32,
                unique=True,
                verbose_name='tipo de notificacao',
            ),
        ),
    ]
