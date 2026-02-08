from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .audit import record_audit


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    record_audit(
        action='Login no sistema',
        user=user,
        request=request,
        details='Usuario autenticado com sucesso.',
        location='Tela de login',
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    if not user:
        return
    record_audit(
        action='Logout do sistema',
        user=user,
        request=request,
        details='Sessao encerrada.',
        location='Logout',
    )
