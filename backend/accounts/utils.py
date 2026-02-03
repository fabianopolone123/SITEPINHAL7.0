import base64
import uuid

from django.core.files.base import ContentFile


def decode_signature(data_url, role_slug):
    if not data_url:
        return None
    if ',' not in data_url:
        return None
    header, encoded = data_url.split(',', 1)
    try:
        decoded = base64.b64decode(encoded)
    except (TypeError, ValueError):
        return None
    ext = 'png'
    filename = f"{role_slug}_{uuid.uuid4().hex}.{ext}"
    return ContentFile(decoded, name=filename)
