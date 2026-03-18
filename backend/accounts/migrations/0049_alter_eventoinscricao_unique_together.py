from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0048_eventocusto'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='eventoinscricao',
            unique_together=set(),
        ),
    ]
