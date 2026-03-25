from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0063_whatsappgatewayconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='pagina_ativa',
            field=models.BooleanField(default=True, verbose_name='pagina do evento ativa'),
        ),
    ]

