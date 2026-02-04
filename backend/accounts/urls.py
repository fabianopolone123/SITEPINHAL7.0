from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.views import LoginView, LogoutView

from .views import (
    RegisterView,
    ResponsavelView,
    AventuraView,
    ConfirmacaoView,
)

app_name = 'accounts'

urlpatterns = [
    # Página inicial -> login
    path('', RedirectView.as_view(pattern_name='accounts:login', permanent=False)),
    path('register/', RegisterView.as_view(), name='register'),
    path('responsavel/', ResponsavelView.as_view(), name='responsavel'),
    path('aventura/', AventuraView.as_view(), name='aventura'),
    path('confirmacao/', ConfirmacaoView.as_view(), name='confirmacao'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='accounts:login'), name='logout'),
]
