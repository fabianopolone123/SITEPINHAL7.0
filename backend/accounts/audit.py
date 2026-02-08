from django.utils import timezone

from .models import AuditLog


def _client_ip_from_request(request):
    if not request:
        return ''
    forwarded = (request.META.get('HTTP_X_FORWARDED_FOR') or '').strip()
    if forwarded:
        return forwarded.split(',')[0].strip()
    return (request.META.get('REMOTE_ADDR') or '').strip()


def _profile_from_user(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return ''
    access = getattr(user, 'access', None)
    if not access:
        return ''
    labels = access.get_profiles_display()
    return ', '.join(labels) if labels else ''


def record_audit(action, user=None, request=None, details='', location='', method='', path=''):
    if not action:
        return
    username = ''
    if user and getattr(user, 'is_authenticated', False):
        username = user.username or ''
    elif request and getattr(request, 'user', None) and getattr(request.user, 'is_authenticated', False):
        user = request.user
        username = request.user.username or ''

    req_method = method or (request.method if request else '')
    req_path = path or (request.path if request else '')
    req_location = location or req_path
    user_agent = ''
    if request:
        user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:255]

    AuditLog.objects.create(
        user=user if user and getattr(user, 'is_authenticated', False) else None,
        username=username,
        profile=_profile_from_user(user),
        location=req_location[:255],
        action=action[:255],
        details=(details or '')[:4000],
        method=(req_method or '')[:12],
        path=(req_path or '')[:255],
        ip_address=_client_ip_from_request(request)[:64],
        user_agent=user_agent,
    )


def now_label():
    return timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S')
