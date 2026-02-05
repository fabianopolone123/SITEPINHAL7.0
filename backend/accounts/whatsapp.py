import json
import os
import re
from datetime import datetime
from urllib import error, request

from django.db import transaction
from django.utils import timezone

from .models import WhatsAppPreference, WhatsAppQueue


def normalize_phone_number(raw_phone):
    if not raw_phone:
        return ''
    digits = re.sub(r'\D', '', raw_phone)
    if not digits:
        return ''
    if digits.startswith('55'):
        return digits
    if len(digits) >= 10:
        return f'55{digits}'
    return digits


def resolve_user_phone(user):
    if hasattr(user, 'whatsapp_preference') and user.whatsapp_preference.phone_number:
        return user.whatsapp_preference.phone_number
    if hasattr(user, 'diretoria') and user.diretoria.whatsapp:
        return user.diretoria.whatsapp
    if hasattr(user, 'responsavel'):
        responsavel = user.responsavel
        return (
            responsavel.responsavel_celular
            or responsavel.mae_celular
            or responsavel.pai_celular
            or responsavel.responsavel_telefone
            or responsavel.mae_telefone
            or responsavel.pai_telefone
            or ''
        )
    return ''


def enqueue_notification(user, notification_type, message_text):
    preference, _ = WhatsAppPreference.objects.get_or_create(user=user)
    if not preference.enabled_for(notification_type):
        return None

    phone_number = normalize_phone_number(preference.phone_number or resolve_user_phone(user))
    if not phone_number:
        return None

    return WhatsAppQueue.objects.create(
        user=user,
        phone_number=phone_number,
        notification_type=notification_type,
        message_text=message_text.strip(),
        status=WhatsAppQueue.STATUS_PENDING,
    )


def _wapi_url():
    instance = os.environ.get('WAPI_INSTANCE', '').strip()
    custom_url = os.environ.get('WAPI_URL', '').strip()
    if custom_url:
        return custom_url
    return f'https://api.w-api.app/v1/message/send-text?instanceId={instance}'


def send_wapi_text(phone_number, message_text):
    url = _wapi_url()
    token = os.environ.get('WAPI_TOKEN', '').strip()
    if not url or 'instanceId=' not in url:
        return False, '', 'WAPI_URL/WAPI_INSTANCE nao configurado.'
    if not token:
        return False, '', 'WAPI_TOKEN nao configurado.'

    payload = json.dumps({
        'phone': phone_number,
        'message': message_text,
    }).encode('utf-8')
    req = request.Request(url=url, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {token}')
    try:
        with request.urlopen(req, timeout=30) as response:
            body = response.read().decode('utf-8', errors='ignore')
            provider_id = ''
            try:
                parsed = json.loads(body) if body else {}
                provider_id = str(
                    parsed.get('messageId')
                    or parsed.get('id')
                    or parsed.get('message', {}).get('id')
                    or ''
                )
            except json.JSONDecodeError:
                provider_id = ''
            return True, provider_id, ''
    except error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='ignore')
        return False, '', f'HTTP {exc.code}: {body[:250]}'
    except Exception as exc:  # noqa: BLE001
        return False, '', str(exc)


@transaction.atomic
def process_next_queue_item():
    item = (
        WhatsAppQueue.objects
        .select_for_update(skip_locked=True)
        .filter(status=WhatsAppQueue.STATUS_PENDING)
        .order_by('created_at')
        .first()
    )
    if not item:
        return None

    success, provider_id, error_message = send_wapi_text(item.phone_number, item.message_text)
    item.attempts += 1
    if success:
        item.status = WhatsAppQueue.STATUS_SENT
        item.provider_message_id = provider_id
        item.sent_at = timezone.now()
        item.last_error = ''
    else:
        item.status = WhatsAppQueue.STATUS_FAILED
        item.last_error = error_message
    item.save(update_fields=['status', 'attempts', 'provider_message_id', 'sent_at', 'last_error'])
    return item


def queue_stats():
    return {
        'pending': WhatsAppQueue.objects.filter(status=WhatsAppQueue.STATUS_PENDING).count(),
        'sent': WhatsAppQueue.objects.filter(status=WhatsAppQueue.STATUS_SENT).count(),
        'failed': WhatsAppQueue.objects.filter(status=WhatsAppQueue.STATUS_FAILED).count(),
        'updated_at': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }
