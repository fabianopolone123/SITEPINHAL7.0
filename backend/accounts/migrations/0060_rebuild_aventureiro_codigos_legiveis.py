import random
import unicodedata

from django.db import migrations


def _normalize_code(raw_value):
    text = unicodedata.normalize('NFKD', str(raw_value or ''))
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = ''.join(ch for ch in text.upper() if ch.isalnum())
    return text[:12]


def _base_from_name(raw_name):
    tokens = []
    for part in str(raw_name or '').strip().split():
        token = _normalize_code(part)
        if token:
            tokens.append(token)
    if not tokens:
        return 'AVENTUREIRO'
    first = tokens[0]
    last = tokens[-1] if len(tokens) > 1 else tokens[0]
    prefix = (first[:1] + last[:1]).ljust(2, 'X')
    body = first if len(first) >= 3 else last
    if not body:
        body = 'AVENTUREIRO'
    return f'{prefix}{body}'[:12]


def _next_unique(base, used):
    if base not in used:
        return base
    for attempt in range(1, 100):
        candidate = f'{base[:10]}{attempt:02d}'
        if candidate not in used:
            return candidate
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    rng = random.SystemRandom()
    for _ in range(500):
        suffix = ''.join(rng.choice(alphabet) for _ in range(4))
        candidate = f'{base[:8]}{suffix}'[:12]
        if candidate not in used:
            return candidate
    return f'AV{len(used)+1:010d}'[-12:]


def rebuild_codes(apps, schema_editor):
    Aventureiro = apps.get_model('accounts', 'Aventureiro')
    aventureiros = list(Aventureiro.objects.all().order_by('id'))
    used = set()
    for av in aventureiros:
        base = _base_from_name(getattr(av, 'nome', ''))
        candidate = _next_unique(base, used)
        used.add(candidate)
        if getattr(av, 'codigo_indicacao', '') != candidate:
            av.codigo_indicacao = candidate
            av.save(update_fields=['codigo_indicacao'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0059_alter_whatsappqueue_notification_type_and_more'),
    ]

    operations = [
        migrations.RunPython(rebuild_codes, migrations.RunPython.noop),
    ]

