from decimal import Decimal
from django.db import migrations


def backfill_valor_estornado(apps, schema_editor):
    EventoInscricao = apps.get_model('accounts', 'EventoInscricao')
    qs = EventoInscricao.objects.filter(cancelada=True, valor_estornado=Decimal('0.00'))
    for inscricao in qs.iterator():
        valor = Decimal(getattr(inscricao, 'valor_inscricao', Decimal('0.00')) or Decimal('0.00')).quantize(Decimal('0.01'))
        if valor <= 0:
            continue
        inscricao.valor_estornado = valor
        inscricao.save(update_fields=['valor_estornado'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0076_eventoinscricao_valor_estornado'),
    ]

    operations = [
        migrations.RunPython(backfill_valor_estornado, migrations.RunPython.noop),
    ]
