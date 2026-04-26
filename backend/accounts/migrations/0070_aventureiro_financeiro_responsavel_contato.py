from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0069_aventureiro_financeiro_responsavel'),
    ]

    operations = [
        migrations.AddField(
            model_name='aventureiro',
            name='financeiro_responsavel_contato',
            field=models.CharField(blank=True, max_length=32, verbose_name='contato financeiro'),
        ),
    ]
