from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0065_evento_event_inactive_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='mensalidadeaventureiro',
            name='cobranca_whatsapp_enviada_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='cobranca whatsapp enviada em'),
        ),
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
                    ('cobranca_mensalidade', 'Cobranca mensalidade em aberto'),
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
                    ('cobranca_mensalidade', 'Cobranca mensalidade em aberto'),
                    ('teste', 'Teste'),
                    ('indicacao_codigo', 'Codigo de indicacao'),
                ],
                max_length=32,
                unique=True,
                verbose_name='tipo de notificacao',
            ),
        ),
    ]

