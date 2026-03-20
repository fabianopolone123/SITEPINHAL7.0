from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0054_evento_event_description'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='mostrar_no_menu_responsavel',
            field=models.BooleanField(default=False, verbose_name='mostrar botao no perfil responsavel'),
        ),
    ]