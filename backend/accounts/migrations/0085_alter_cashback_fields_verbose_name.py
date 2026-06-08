from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0084_cashback_mensalidade'),
    ]

    operations = [
        # Remove verbose_name para alinhar com o model atual
        migrations.AlterField(
            model_name='pagamentomensalidade',
            name='cashback_aventureiro',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pagamentos_mensalidade_cashback',
                to='accounts.aventureiro',
            ),
        ),
        migrations.AlterField(
            model_name='aventureirocashbacklancamento',
            name='pagamento_mensalidade',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='cashback_lancamentos',
                to='accounts.pagamentomensalidade',
            ),
        ),
    ]
