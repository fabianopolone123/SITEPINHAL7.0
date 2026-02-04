from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.views import LoginView, LogoutView

from .views import (
    RegisterView,
    ResponsavelView,
    DiretoriaView,
    AventuraView,
    ConfirmacaoView,
    PainelView,
    MeusDadosView,
    MeuResponsavelDetalheView,
    MeuResponsavelEditarView,
    MeuAventureiroDetalheView,
    MeuAventureiroEditarView,
    MinhaDiretoriaDetalheView,
    MinhaDiretoriaEditarView,
    AventureirosGeraisView,
    UsuariosView,
    UsuarioPermissaoEditarView,
)

app_name = 'accounts'

urlpatterns = [
    # Página inicial -> login
    path('', RedirectView.as_view(pattern_name='accounts:login', permanent=False)),
    path('register/', RegisterView.as_view(), name='register'),
    path('responsavel/', ResponsavelView.as_view(), name='responsavel'),
    path('diretoria/', DiretoriaView.as_view(), name='diretoria'),
    path('aventura/', AventuraView.as_view(), name='aventura'),
    path('confirmacao/', ConfirmacaoView.as_view(), name='confirmacao'),
    path('painel/', PainelView.as_view(), name='painel'),
    path('meus-dados/', MeusDadosView.as_view(), name='meus_dados'),
    path('meus-dados/responsavel/', MeuResponsavelDetalheView.as_view(), name='meu_responsavel'),
    path('meus-dados/responsavel/editar/', MeuResponsavelEditarView.as_view(), name='editar_meu_responsavel'),
    path('meus-dados/diretoria/', MinhaDiretoriaDetalheView.as_view(), name='minha_diretoria'),
    path('meus-dados/diretoria/editar/', MinhaDiretoriaEditarView.as_view(), name='editar_minha_diretoria'),
    path('meus-dados/aventureiro/<int:pk>/', MeuAventureiroDetalheView.as_view(), name='meu_aventureiro'),
    path('meus-dados/aventureiro/<int:pk>/editar/', MeuAventureiroEditarView.as_view(), name='editar_meu_aventureiro'),
    path('usuarios/', UsuariosView.as_view(), name='usuarios'),
    path('usuarios/<int:pk>/editar/', UsuarioPermissaoEditarView.as_view(), name='editar_usuario_permissoes'),
    path('aventureiros-gerais/', AventureirosGeraisView.as_view(), name='aventureiros_gerais'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='accounts:login'), name='logout'),
]
