from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def add_apostila_to_default_groups(apps, schema_editor):
    AccessGroup = apps.get_model('accounts', 'AccessGroup')
    for code in ('diretor', 'professor'):
        group = AccessGroup.objects.filter(code=code).first()
        if not group:
            continue
        current = []
        seen = set()
        for item in group.menu_permissions or []:
            key = str(item or '').strip()
            if key and key not in seen:
                current.append(key)
                seen.add(key)
        if 'apostila' not in seen:
            current.append('apostila')
            group.menu_permissions = current
            group.save(update_fields=['menu_permissions', 'updated_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0037_lojapedido_entregue'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApostilaRequisito',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('classe', models.CharField(choices=[('abelhinhas', 'Abelhinhas'), ('luminares', 'Luminares'), ('edificadores', 'Edificadores'), ('maos_ajudadoras', 'Mãos Ajudadoras')], max_length=32, verbose_name='classe')),
                ('numero_requisito', models.CharField(max_length=64, verbose_name='número do requisito')),
                ('descricao', models.TextField(verbose_name='descrição')),
                ('resposta', models.TextField(blank=True, verbose_name='resposta')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='apostila_requisitos_criados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'requisito da apostila',
                'verbose_name_plural': 'requisitos da apostila',
                'ordering': ('classe', 'numero_requisito', 'id'),
            },
        ),
        migrations.RunPython(add_apostila_to_default_groups, migrations.RunPython.noop),
    ]
