from django.urls import resolve

from .audit import record_audit


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.method not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            return response
        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return response
        if request.path.startswith('/admin/'):
            return response

        action = ''
        details = ''
        try:
            match = resolve(request.path)
            if match and match.view_name:
                action = f'Acao no sistema: {match.view_name}'
        except Exception:
            action = ''
        if not action:
            action = 'Acao no sistema'

        raw_action = (request.POST.get('action') or '').strip()
        if raw_action:
            details = f'action={raw_action}'

        record_audit(
            action=action,
            user=user,
            request=request,
            details=details,
            location=request.path,
        )
        return response
