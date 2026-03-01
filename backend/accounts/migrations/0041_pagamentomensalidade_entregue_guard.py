from django.db import migrations, models


def _ensure_pagamento_entregue_column(apps, schema_editor):
    table_name = 'accounts_pagamentomensalidade'
    quoted_table = schema_editor.quote_name(table_name)
    quoted_column = schema_editor.quote_name('entregue')
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        columns = [col.name for col in connection.introspection.get_table_description(cursor, table_name)]

    if 'entregue' in columns:
        with connection.cursor() as cursor:
            cursor.execute(f'UPDATE {quoted_table} SET {quoted_column} = 0 WHERE {quoted_column} IS NULL')
        return

    with connection.cursor() as cursor:
        if connection.vendor == 'postgresql':
            cursor.execute(f'ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} boolean NOT NULL DEFAULT false')
        else:
            cursor.execute(f'ALTER TABLE {quoted_table} ADD COLUMN {quoted_column} bool NOT NULL DEFAULT 0')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0040_apostiladica_apostiladicaarquivo_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(_ensure_pagamento_entregue_column, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='pagamentomensalidade',
                    name='entregue',
                    field=models.BooleanField(default=False, verbose_name='entregue'),
                ),
            ],
        ),
    ]
