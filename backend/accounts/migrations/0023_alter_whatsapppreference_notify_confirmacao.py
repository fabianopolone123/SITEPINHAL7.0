from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_auditlog'),
    ]

    operations = [
        migrations.AlterField(
            model_name='whatsapppreference',
            name='notify_confirmacao',
            field=models.BooleanField(default=False, verbose_name='notificacao de confirmacao de inscricao'),
        ),
    ]
