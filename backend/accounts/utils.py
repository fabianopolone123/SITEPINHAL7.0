import base64
import uuid

from django.core.files.base import ContentFile


def decode_data_url(data_url, prefix, ext='png'):
    if not data_url:
        return None
    if ',' not in data_url:
        return None
    _, encoded = data_url.split(',', 1)
    try:
        decoded = base64.b64decode(encoded)
    except (TypeError, ValueError):
        return None
    filename = f'{prefix}_{uuid.uuid4().hex}.{ext}'
    return ContentFile(decoded, name=filename)


def decode_signature(data_url, role_slug):
    return decode_data_url(data_url, f'{role_slug}_signature')


def decode_photo(data_url):
    return decode_data_url(data_url, 'aventura_photo')
