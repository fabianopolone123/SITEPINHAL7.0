from django.urls import resolve

from .audit import record_audit


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        user = getattr(request, 'user', None)
        if not user or not getattr(user, 'is_authenticated', False):
            return response
        path = request.path or ''
        if (
            path.startswith('/admin/')
            or path.startswith('/static/')
            or path.startswith('/media/')
        ):
            return response

        action = ''
        details = ''
        view_name = ''
        try:
            match = resolve(request.path)
            if match and match.view_name:
                view_name = match.view_name
        except Exception:
            view_name = ''

        is_api = bool(view_name and view_name.endswith('_api'))
        if request.method == 'GET':
            if is_api or path.endswith('/presenca/status/'):
                return response
            action = f'Acesso de tela: {view_name or path}'
            details = f'method=GET status={response.status_code}'
        elif request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            action = f'Acao no sistema: {view_name or path}'
            raw_action = (request.POST.get('action') or '').strip()
            if raw_action:
                details = f'action={raw_action}'
        else:
            return response

        if not action:
            return response

        record_audit(
            action=action,
            user=user,
            request=request,
            details=details[:4000],
            location=request.path,
        )
        return response
