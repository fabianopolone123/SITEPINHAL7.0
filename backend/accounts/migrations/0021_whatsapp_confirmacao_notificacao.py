from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_eventopresenca'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsapppreference',
            name='notify_confirmacao',
            field=models.BooleanField(default=True, verbose_name='notificacao de confirmacao de inscricao'),
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
                    ('geral', 'Geral'),
                    ('teste', 'Teste'),
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
                    ('teste', 'Teste'),
                ],
                max_length=32,
                unique=True,
                verbose_name='tipo de notificacao',
            ),
        ),
    ]
