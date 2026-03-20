from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0056_whatsapp_evento_inscricao_notificacao'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventoinscricao',
            name='confirmada',
            field=models.BooleanField(default=True, verbose_name='inscricao confirmada por pagamento'),
        ),
        migrations.AddField(
            model_name='lojapedido',
            name='evento_inscricao',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pedidos_evento', to='accounts.eventoinscricao'),
        ),
    ]
