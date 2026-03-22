from decimal import Decimal
import random
import re

from django.db import migrations, models
import django.db.models.deletion


def _backfill_codigo_indicacao(apps, schema_editor):
    Aventureiro = apps.get_model('accounts', 'Aventureiro')
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    rng = random.SystemRandom()

    used = set()

    aventureiros = Aventureiro.objects.all().order_by('id')
    for av in aventureiros.iterator():
        normalized = re.sub(r'[^A-Z0-9]', '', str(getattr(av, 'codigo_indicacao', '') or '').upper())[:12]
        candidate = ''
        if normalized and normalized not in used:
            candidate = normalized
        if not candidate:
            for _ in range(120):
                maybe = ''.join(rng.choice(alphabet) for _ in range(6))
                if maybe and maybe not in used:
                    candidate = maybe
                    break
        if not candidate:
            candidate = f'AV{int(av.id):010d}'[-12:]
            suffix = 0
            while candidate in used:
                suffix += 1
                candidate = (f'AV{int(av.id):08d}{suffix:02d}')[-12:]
        used.add(candidate)
        if getattr(av, 'codigo_indicacao', '') != candidate:
            av.codigo_indicacao = candidate
            av.save(update_fields=['codigo_indicacao'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0057_eventoinscricao_confirmada_and_lojapedido_evento_inscricao'),
    ]

    operations = [
        migrations.AddField(
            model_name='aventureiro',
            name='cashback_saldo',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='saldo cashback'),
        ),
        migrations.AddField(
            model_name='aventureiro',
            name='codigo_indicacao',
            field=models.CharField(blank=True, db_index=True, default='', max_length=12, verbose_name='codigo de indicacao'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eventoinscricao',
            name='cashback_creditado',
            field=models.BooleanField(default=False, verbose_name='cashback creditado'),
        ),
        migrations.AddField(
            model_name='eventoinscricao',
            name='cashback_creditado_valor',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='valor cashback creditado'),
        ),
        migrations.AddField(
            model_name='eventoinscricao',
            name='cashback_usado_valor',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='valor cashback usado'),
        ),
        migrations.AddField(
            model_name='eventoinscricao',
            name='codigo_indicacao_usado',
            field=models.CharField(blank=True, max_length=12, verbose_name='codigo indicacao usado'),
        ),
        migrations.AddField(
            model_name='eventoinscricao',
            name='indicador_aventureiro',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inscricoes_indicadas', to='accounts.aventureiro'),
        ),
        migrations.AddField(
            model_name='lojapedido',
            name='cashback_desconto_valor',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='desconto cashback'),
        ),
        migrations.AddField(
            model_name='lojapedido',
            name='cashback_aventureiro',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pedidos_loja_cashback', to='accounts.aventureiro'),
        ),
        migrations.CreateModel(
            name='AventureiroCashbackLancamento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('credito_indicacao', 'Credito por indicacao'), ('debito_uso', 'Debito por uso')], max_length=24, verbose_name='tipo')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='valor')),
                ('saldo_apos', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, verbose_name='saldo apos lancamento')),
                ('descricao', models.CharField(blank=True, max_length=255, verbose_name='descricao')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='criado em')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='atualizado em')),
                ('aventureiro', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cashback_lancamentos', to='accounts.aventureiro')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cashback_lancamentos_criados', to='auth.user')),
                ('evento_inscricao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cashback_lancamentos', to='accounts.eventoinscricao')),
                ('loja_pedido', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cashback_lancamentos', to='accounts.lojapedido')),
            ],
            options={
                'verbose_name': 'lancamento de cashback',
                'verbose_name_plural': 'lancamentos de cashback',
                'ordering': ('-created_at', 'id'),
            },
        ),
        migrations.RunPython(_backfill_codigo_indicacao, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='aventureiro',
            name='codigo_indicacao',
            field=models.CharField(blank=True, db_index=True, max_length=12, unique=True, verbose_name='codigo de indicacao'),
        ),
    ]
