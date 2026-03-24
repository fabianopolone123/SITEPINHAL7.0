from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0062_whatsapp_evento_templates_split'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='WhatsAppGatewayConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wapi_token', models.CharField(blank=True, max_length=512, verbose_name='token W-API')),
                ('wapi_instance', models.CharField(blank=True, max_length=128, verbose_name='instance W-API')),
                ('wapi_url', models.CharField(blank=True, max_length=512, verbose_name='URL W-API')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='whatsapp_gateway_configs_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'configuração do gateway WhatsApp',
                'verbose_name_plural': 'configurações do gateway WhatsApp',
            },
        ),
    ]

