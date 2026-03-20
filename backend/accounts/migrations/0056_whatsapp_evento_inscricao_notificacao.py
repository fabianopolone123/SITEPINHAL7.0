from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0055_evento_mostrar_no_menu_responsavel'),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsapppreference',
            name='notify_evento_inscricao',
            field=models.BooleanField(default=False, verbose_name='notificacao de nova inscricao de evento'),
        ),
        migrations.AlterField(
            model_name='whatsappqueue',
            name='notification_type',
            field=models.CharField(choices=[('cadastro', 'Cadastro'), ('diretoria', 'Diretoria'), ('confirmacao', 'Confirma\u00e7\u00e3o'), ('financeiro', 'Financeiro'), ('loja', 'Loja'), ('evento_inscricao', 'Nova inscricao de evento'), ('geral', 'Geral'), ('teste', 'Teste')], default='geral', max_length=32, verbose_name='tipo notificacao'),
        ),
        migrations.AlterField(
            model_name='whatsapptemplate',
            name='notification_type',
            field=models.CharField(choices=[('cadastro', 'Cadastro'), ('diretoria', 'Diretoria'), ('confirmacao', 'Confirma\u00e7\u00e3o'), ('financeiro', 'Financeiro'), ('loja', 'Loja'), ('evento_inscricao', 'Nova inscricao de evento'), ('teste', 'Teste')], max_length=32, unique=True, verbose_name='tipo de notificacao'),
        ),
    ]
