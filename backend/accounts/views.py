import copy

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils import timezone

from .forms import (
    ResponsavelForm,
    DiretoriaForm,
    AventureiroForm,
    ResponsavelDadosForm,
    AventureiroDadosForm,
    DiretoriaDadosForm,
    UserAccessForm,
)
from .models import (
    Responsavel,
    Aventureiro,
    Diretoria,
    UserAccess,
    WhatsAppPreference,
    WhatsAppQueue,
    WhatsAppTemplate,
)
from .utils import decode_signature, decode_photo
from .whatsapp import (
    queue_stats,
    resolve_user_phone,
    send_wapi_text,
    normalize_phone_number,
    render_message,
    get_template_message,
)
from datetime import date

User = get_user_model()


def _get_pending_aventures(session):
    return session.get('aventures_pending', [])


def _ensure_user_access(user):
    access = getattr(user, 'access', None)
    if access:
        return access
    if hasattr(user, 'diretoria'):
        role = UserAccess.ROLE_DIRETORIA
    else:
        role = UserAccess.ROLE_RESPONSAVEL
    access, _ = UserAccess.objects.get_or_create(user=user, defaults={'role': role})
    if not access.profiles:
        access.profiles = [access.role]
        access.save(update_fields=['profiles', 'updated_at'])
    return access


def _is_diretor(user):
    return _ensure_user_access(user).has_profile(UserAccess.ROLE_DIRETOR)


def _sidebar_context(request):
    access = _ensure_user_access(request.user)
    return {
        'is_diretor': access.has_profile(UserAccess.ROLE_DIRETOR),
        'current_profiles': access.get_profiles_display(),
    }


def _profile_order_weight(access):
    profiles = set(access.profiles or [])
    if access.role:
        profiles.add(access.role)
    if UserAccess.ROLE_DIRETORIA in profiles or UserAccess.ROLE_DIRETOR in profiles:
        return 0
    if UserAccess.ROLE_RESPONSAVEL in profiles:
        return 1
    return 2


def _user_display_data(user):
    foto_url = ''
    nome_completo = user.get_full_name().strip()
    if hasattr(user, 'diretoria'):
        diretoria = user.diretoria
        nome_completo = diretoria.nome or nome_completo
        if diretoria.foto:
            foto_url = diretoria.foto.url
    elif hasattr(user, 'responsavel'):
        responsavel = user.responsavel
        nome_completo = (
            responsavel.responsavel_nome
            or responsavel.mae_nome
            or responsavel.pai_nome
            or nome_completo
        )
    return {
        'nome_completo': nome_completo or user.username,
        'foto_url': foto_url,
    }


def _set_pending_aventures(session, pending):
    session['aventures_pending'] = pending
    session.modified = True


def _clear_pending_aventures(session):
    _set_pending_aventures(session, [])


def _pending_count(session):
    return len(_get_pending_aventures(session))


def _dispatch_cadastro_notifications(tipo_cadastro, user, nome):
    responsavel_nome = '-'
    aventureiros = '-'
    responsavel = getattr(user, 'responsavel', None)
    if responsavel:
        responsavel_nome = (
            responsavel.responsavel_nome
            or responsavel.mae_nome
            or responsavel.pai_nome
            or user.username
        )
        aventura_nomes = list(responsavel.aventures.order_by('nome').values_list('nome', flat=True))
        aventureiros = ', '.join(aventura_nomes) if aventura_nomes else '-'

    payload = {
        'tipo_cadastro': tipo_cadastro,
        'username': user.username,
        'nome': nome or user.username,
        'responsavel_nome': responsavel_nome,
        'aventureiros': aventureiros,
        'data_hora': timezone.now().strftime('%d/%m/%Y %H:%M'),
    }
    template_text = get_template_message(WhatsAppTemplate.TYPE_CADASTRO)
    prefs = WhatsAppPreference.objects.filter(notify_cadastro=True)
    for pref in prefs.select_related('user'):
        phone_number = normalize_phone_number(pref.phone_number or resolve_user_phone(pref.user))
        if not phone_number:
            continue
        text = render_message(template_text, payload)
        queue_item = WhatsAppQueue.objects.create(
            user=pref.user,
            phone_number=phone_number,
            notification_type=WhatsAppQueue.TYPE_CADASTRO,
            message_text=text,
            status=WhatsAppQueue.STATUS_PENDING,
        )
        success, provider_id, error_message = send_wapi_text(phone_number, text)
        queue_item.attempts = 1
        if success:
            queue_item.status = WhatsAppQueue.STATUS_SENT
            queue_item.provider_message_id = provider_id
            queue_item.sent_at = timezone.now()
            queue_item.last_error = ''
        else:
            queue_item.status = WhatsAppQueue.STATUS_FAILED
            queue_item.last_error = error_message
        queue_item.save(update_fields=['status', 'attempts', 'provider_message_id', 'sent_at', 'last_error'])


def _serialize_field_value(value):
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, dict)):
        return value
    return value


def _deserialize_fields(fields):
    result = {}
    for key, value in fields.items():
        if key == 'nascimento' and isinstance(value, str):
            try:
                result[key] = date.fromisoformat(value)
            except ValueError:
                result[key] = value
            continue
        result[key] = value
    return result


AVENTUREIRO_FIELDS = {
    'nome', 'sexo', 'nascimento', 'serie', 'colegio', 'bolsa', 'religiao',
    'certidao', 'rg', 'orgao', 'cpf', 'camiseta', 'plano', 'plano_nome',
    'cns', 'doencas', 'condicoes', 'alergias', 'deficiencias',
    'tipo_sangue', 'declaracao_medica', 'autorizacao_imagem',
}


def _enqueue_pending_aventure(session, cleaned_data):
    pending = list(_get_pending_aventures(session))
    fields = {
        key: _serialize_field_value(copy.deepcopy(cleaned_data.get(key)))
        for key in AVENTUREIRO_FIELDS
        if key in cleaned_data
    }
    entry = {
        'fields': fields,
        'signature': cleaned_data.get('signature_value_av', '').strip() or None,
        'photo': cleaned_data.get('photo_value', '').strip() or None,
    }
    pending.append(entry)
    _set_pending_aventures(session, pending)


class RegisterView(View):
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name)


class LogoutRedirectView(View):
    def get(self, request):
        logout(request)
        messages.success(request, 'Sessão encerrada. Faça login para continuar.')
        return redirect('accounts:login')

    def post(self, request):
        return self.get(request)


class ResponsavelView(View):
    template_name = 'responsavel.html'

    def get(self, request):
        form = ResponsavelForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ResponsavelForm(request.POST)
        if form.is_valid():
            responsavel = form.save()
            login(request, responsavel.user)
            messages.success(request, 'Responsável cadastrado com sucesso. Continue com a ficha do aventureiro.')
            return redirect('accounts:aventura')
        messages.error(request, 'Há campos obrigatórios pendentes; corrija e envie novamente.')
        return render(request, self.template_name, {'form': form})


class DiretoriaView(View):
    template_name = 'diretoria.html'

    def get(self, request):
        form = DiretoriaForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = DiretoriaForm(request.POST)
        if form.is_valid():
            diretoria = form.save()
            _dispatch_cadastro_notifications('Diretoria', diretoria.user, diretoria.nome)
            messages.success(request, 'Cadastro da diretoria concluído com sucesso. Faça login para continuar.')
            return redirect('accounts:login')
        messages.error(request, 'Há campos obrigatórios pendentes; corrija e envie novamente.')
        return render(request, self.template_name, {'form': form})


class AventuraView(LoginRequiredMixin, View):
    template_name = 'aventura.html'

    def _current_sequence_for(self, request, responsavel=None):
        responsavel = responsavel or getattr(request.user, 'responsavel', None)
        saved = responsavel.aventures.count() if responsavel else 0
        return saved + _pending_count(request.session) + 1

    def _build_context(self, form, request, responsavel):
        return {
            'form': form,
            'current_sequence': self._current_sequence_for(request, responsavel),
            'pending_count': _pending_count(request.session),
        }

    def get(self, request):
        responsavel = getattr(request.user, 'responsavel', None)
        if not responsavel:
            messages.error(request, 'Complete primeiro os dados do responsável para continuar.')
            return redirect('accounts:responsavel')
        form = AventureiroForm()
        return render(request, self.template_name, self._build_context(form, request, responsavel))

    def post(self, request):
        responsavel = getattr(request.user, 'responsavel', None)
        if not responsavel:
            messages.error(request, 'Complete primeiro os dados do responsável para continuar.')
            return redirect('accounts:responsavel')
        form = AventureiroForm(request.POST)
        if form.is_valid():
            _enqueue_pending_aventure(request.session, form.cleaned_data)
            action = request.POST.get('action', 'save_confirm')
            messages.success(request, 'Ficha salva e encaminhada para revisão. Vá para a confirmação para concluir o cadastro.')
            if action == 'add_more':
                form = AventureiroForm()
                return render(request, self.template_name, self._build_context(form, request, responsavel))
            return redirect('accounts:confirmacao')
        messages.error(request, 'Verifique os campos antes de salvar o aventureiro.')
        return render(request, self.template_name, self._build_context(form, request, responsavel))


class ConfirmacaoView(LoginRequiredMixin, View):
    template_name = 'confirmacao.html'

    def get(self, request):
        responsavel = getattr(request.user, 'responsavel', None)
        if not responsavel:
            messages.error(request, 'Complete os dados do responsável antes de revisar os aventureiros.')
            return redirect('accounts:responsavel')
        pending = _get_pending_aventures(request.session)
        context = {
            'responsavel': responsavel,
            'aventures': responsavel.aventures.all(),
            'pending_aventures': [
                {'fields': entry['fields'], 'photo': entry.get('photo')}
                for entry in pending
            ],
            'pending_count': len(pending),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        responsavel = getattr(request.user, 'responsavel', None)
        if not responsavel:
            messages.error(request, 'Complete os dados do responsável antes de revisar os aventureiros.')
            return redirect('accounts:responsavel')
        pending = _get_pending_aventures(request.session)
        if not pending:
            messages.error(request, 'Não há fichas pendentes para confirmar.')
            return redirect('accounts:confirmacao')
        for entry in pending:
            raw_fields = entry.get('fields', {})
            fields = _deserialize_fields(raw_fields)
            fields = {k: v for k, v in fields.items() if k in AVENTUREIRO_FIELDS}
            signature_data = entry.get('signature')
            aventureiro = Aventureiro(responsavel=responsavel, **fields)
            if signature_data:
                signature_file = decode_signature(signature_data, 'aventura')
                if signature_file:
                    aventureiro.assinatura.save(signature_file.name, signature_file, save=False)
            photo_data = entry.get('photo')
            if photo_data:
                photo_file = decode_photo(photo_data)
                if photo_file:
                    aventureiro.foto.save(photo_file.name, photo_file, save=False)
            aventureiro.save()
        _dispatch_cadastro_notifications(
            'Cadastro completo',
            request.user,
            responsavel.responsavel_nome or responsavel.mae_nome or responsavel.pai_nome,
        )
        _clear_pending_aventures(request.session)
        logout(request)
        messages.success(request, 'Cadastro finalizado com sucesso. Faça login novamente para continuar.')
        return redirect('accounts:login')


class PainelView(LoginRequiredMixin, View):
    template_name = 'painel.html'

    def get(self, request):
        responsavel = getattr(request.user, 'responsavel', None)
        pending_count = len(request.session.get('aventures_pending', []))

        has_responsavel = responsavel is not None
        has_pending = pending_count > 0

        if not has_responsavel:
            primary_action = {
                'label': 'Iniciar cadastro',
                'url_name': 'accounts:responsavel',
            }
        elif has_pending:
            primary_action = {
                'label': 'Revisar e concluir',
                'url_name': 'accounts:confirmacao',
            }
        else:
            primary_action = {
                'label': 'Cadastrar aventureiro',
                'url_name': 'accounts:aventura',
            }

        context = {
            'responsavel': responsavel,
            'pending_count': pending_count,
            'has_responsavel': has_responsavel,
            'has_pending': has_pending,
            'primary_action': primary_action,
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


def _require_responsavel_or_redirect(request):
    responsavel = getattr(request.user, 'responsavel', None)
    if not responsavel:
        messages.error(request, 'Cadastre os dados do responsável antes de acessar esta área.')
        return None, redirect('accounts:responsavel')
    return responsavel, None


class MeusDadosView(LoginRequiredMixin, View):
    template_name = 'meus_dados.html'

    def get(self, request):
        responsavel = getattr(request.user, 'responsavel', None)
        diretoria = getattr(request.user, 'diretoria', None)
        aventureiros = responsavel.aventures.order_by('nome') if responsavel else []

        context = {
            'responsavel': responsavel,
            'diretoria': diretoria,
            'aventureiros': aventureiros,
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class MeuResponsavelDetalheView(LoginRequiredMixin, View):
    template_name = 'meus_dados_responsavel.html'

    def get(self, request):
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        context = {'responsavel': responsavel}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class MeuResponsavelEditarView(LoginRequiredMixin, View):
    template_name = 'meus_dados_responsavel_editar.html'

    def get(self, request):
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        form = ResponsavelDadosForm(instance=responsavel)
        context = {'form': form}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)

    def post(self, request):
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        form = ResponsavelDadosForm(request.POST, instance=responsavel)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dados do responsável atualizados com sucesso.')
            return redirect('accounts:meu_responsavel')
        messages.error(request, 'Verifique os campos e tente novamente.')
        context = {'form': form}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class MeuAventureiroDetalheView(LoginRequiredMixin, View):
    template_name = 'meus_dados_aventureiro.html'

    def get(self, request, pk):
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        aventureiro = get_object_or_404(Aventureiro, pk=pk, responsavel=responsavel)

        condicoes_labels = {
            'cardiaco': 'Problemas cardíacos',
            'diabetico': 'Diabetes',
            'renal': 'Problemas renais',
            'psicologico': 'Problemas psicológicos',
        }
        alergias_labels = {
            'alergia_pele': 'Alergia cutânea (pele)',
            'alergia_alimento': 'Alergia alimentar',
            'alergia_medicamento': 'Alergia a medicamentos',
        }

        condicoes = []
        for key, label in condicoes_labels.items():
            data = (aventureiro.condicoes or {}).get(key, {})
            condicoes.append({
                'label': label,
                'resposta': data.get('resposta') or 'nao',
                'detalhe': data.get('detalhe') or '',
                'medicamento': data.get('medicamento') or 'nao',
                'remedio': data.get('remedio') or '',
            })

        alergias = []
        for key, label in alergias_labels.items():
            data = (aventureiro.alergias or {}).get(key, {})
            alergias.append({
                'label': label,
                'resposta': data.get('resposta') or 'nao',
                'descricao': data.get('descricao') or '',
            })

        context = {
            'aventureiro': aventureiro,
            'condicoes_display': condicoes,
            'alergias_display': alergias,
            'doencas_display': aventureiro.doencas or [],
            'deficiencias_display': aventureiro.deficiencias or [],
            'back_url_name': 'accounts:meus_dados',
            'back_label': 'Voltar para meus dados',
            'can_edit': True,
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class MeuAventureiroEditarView(LoginRequiredMixin, View):
    template_name = 'meus_dados_aventureiro_editar.html'

    def get(self, request, pk):
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        aventureiro = get_object_or_404(Aventureiro, pk=pk, responsavel=responsavel)
        form = AventureiroDadosForm(instance=aventureiro)
        context = {'form': form, 'aventureiro': aventureiro}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)

    def post(self, request, pk):
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        aventureiro = get_object_or_404(Aventureiro, pk=pk, responsavel=responsavel)
        form = AventureiroDadosForm(request.POST, request.FILES, instance=aventureiro)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dados do aventureiro atualizados com sucesso.')
            return redirect('accounts:meu_aventureiro', pk=aventureiro.pk)
        messages.error(request, 'Verifique os campos e tente novamente.')
        context = {'form': form, 'aventureiro': aventureiro}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


def _require_diretoria_or_redirect(request):
    diretoria = getattr(request.user, 'diretoria', None)
    if not diretoria:
        messages.error(request, 'Cadastre os dados da diretoria antes de acessar esta área.')
        return None, redirect('accounts:diretoria')
    return diretoria, None


class MinhaDiretoriaDetalheView(LoginRequiredMixin, View):
    template_name = 'meus_dados_diretoria.html'

    def get(self, request):
        diretoria, redirect_response = _require_diretoria_or_redirect(request)
        if redirect_response:
            return redirect_response
        context = {'diretoria': diretoria}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class MinhaDiretoriaEditarView(LoginRequiredMixin, View):
    template_name = 'meus_dados_diretoria_editar.html'

    def get(self, request):
        diretoria, redirect_response = _require_diretoria_or_redirect(request)
        if redirect_response:
            return redirect_response
        form = DiretoriaDadosForm(instance=diretoria)
        context = {'form': form, 'diretoria': diretoria}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)

    def post(self, request):
        diretoria, redirect_response = _require_diretoria_or_redirect(request)
        if redirect_response:
            return redirect_response
        form = DiretoriaDadosForm(request.POST, instance=diretoria)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dados da diretoria atualizados com sucesso.')
            return redirect('accounts:minha_diretoria')
        messages.error(request, 'Verifique os campos e tente novamente.')
        context = {'form': form, 'diretoria': diretoria}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class AventureirosGeraisView(LoginRequiredMixin, View):
    template_name = 'aventureiros_gerais.html'

    def get(self, request):
        if not _is_diretor(request.user):
            messages.error(request, 'Seu perfil não possui permissão para acessar aventureiros gerais.')
            return redirect('accounts:painel')
        aventureiros = Aventureiro.objects.select_related('responsavel', 'responsavel__user').order_by('nome')
        context = {'aventureiros': aventureiros}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class AventureiroGeralDetalheView(LoginRequiredMixin, View):
    template_name = 'meus_dados_aventureiro.html'

    def get(self, request, pk):
        if not _is_diretor(request.user):
            messages.error(request, 'Seu perfil não possui permissão para visualizar esse aventureiro.')
            return redirect('accounts:painel')
        aventureiro = get_object_or_404(Aventureiro, pk=pk)

        condicoes_labels = {
            'cardiaco': 'Problemas cardíacos',
            'diabetico': 'Diabetes',
            'renal': 'Problemas renais',
            'psicologico': 'Problemas psicológicos',
        }
        alergias_labels = {
            'alergia_pele': 'Alergia cutânea (pele)',
            'alergia_alimento': 'Alergia alimentar',
            'alergia_medicamento': 'Alergia a medicamentos',
        }

        condicoes = []
        for key, label in condicoes_labels.items():
            data = (aventureiro.condicoes or {}).get(key, {})
            condicoes.append({
                'label': label,
                'resposta': data.get('resposta') or 'nao',
                'detalhe': data.get('detalhe') or '',
                'medicamento': data.get('medicamento') or 'nao',
                'remedio': data.get('remedio') or '',
            })

        alergias = []
        for key, label in alergias_labels.items():
            data = (aventureiro.alergias or {}).get(key, {})
            alergias.append({
                'label': label,
                'resposta': data.get('resposta') or 'nao',
                'descricao': data.get('descricao') or '',
            })

        context = {
            'aventureiro': aventureiro,
            'condicoes_display': condicoes,
            'alergias_display': alergias,
            'doencas_display': aventureiro.doencas or [],
            'deficiencias_display': aventureiro.deficiencias or [],
            'back_url_name': 'accounts:aventureiros_gerais',
            'back_label': 'Voltar para aventureiros',
            'can_edit': False,
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class UsuariosView(LoginRequiredMixin, View):
    template_name = 'usuarios.html'

    def get(self, request):
        if not _is_diretor(request.user):
            messages.error(request, 'Seu perfil não possui permissão para acessar usuários.')
            return redirect('accounts:painel')

        users = (
            UserAccess.objects
            .select_related('user', 'user__responsavel', 'user__diretoria')
        )
        user_rows = []
        for access in users:
            display = _user_display_data(access.user)
            user_rows.append({
                'access': access,
                'user': access.user,
                'nome_completo': display['nome_completo'],
                'foto_url': display['foto_url'],
            })
        user_rows.sort(key=lambda row: (_profile_order_weight(row['access']), row['user'].username.lower()))
        context = {'users': user_rows}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class WhatsAppView(LoginRequiredMixin, View):
    template_name = 'whatsapp.html'

    def _director_guard(self, request):
        if not _is_diretor(request.user):
            messages.error(request, 'Seu perfil nao possui permissao para acessar WhatsApp.')
            return redirect('accounts:painel')
        return None

    def _users_context(self):
        rows = []
        accesses = UserAccess.objects.select_related('user', 'user__responsavel', 'user__diretoria').order_by('user__username')
        for access in accesses:
            user = access.user
            pref, _ = WhatsAppPreference.objects.get_or_create(user=user)
            detected_phone = normalize_phone_number(resolve_user_phone(user))
            if not pref.phone_number and detected_phone:
                pref.phone_number = detected_phone
                pref.save(update_fields=['phone_number', 'updated_at'])
            display = _user_display_data(user)
            rows.append({
                'user': user,
                'access': access,
                'pref': pref,
                'nome_completo': display['nome_completo'],
            })
        rows.sort(key=lambda row: (_profile_order_weight(row['access']), row['user'].username.lower()))
        return rows

    def get(self, request):
        guard = self._director_guard(request)
        if guard:
            return guard
        cadastro_template = get_template_message(WhatsAppTemplate.TYPE_CADASTRO)
        teste_template = get_template_message(WhatsAppTemplate.TYPE_TESTE)
        context = {
            'rows': self._users_context(),
            'queue': queue_stats(),
            'cadastro_template': cadastro_template,
            'teste_template': teste_template,
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)

    def post(self, request):
        guard = self._director_guard(request)
        if guard:
            return guard
        rows = self._users_context()
        cadastro_enabled = []
        for row in rows:
            user = row['user']
            pref = row['pref']
            prefix = f'u{user.pk}'
            pref.phone_number = normalize_phone_number(request.POST.get(f'{prefix}_phone', '').strip())
            pref.notify_cadastro = bool(request.POST.get(f'{prefix}_cadastro'))
            pref.notify_financeiro = False
            pref.notify_geral = False
            pref.save(update_fields=['phone_number', 'notify_cadastro', 'notify_financeiro', 'notify_geral', 'updated_at'])
            if pref.notify_cadastro:
                cadastro_enabled.append(user.username)

        WhatsAppTemplate.objects.update_or_create(
            notification_type=WhatsAppTemplate.TYPE_CADASTRO,
            defaults={'message_text': request.POST.get('template_cadastro', '').strip()},
        )
        WhatsAppTemplate.objects.update_or_create(
            notification_type=WhatsAppTemplate.TYPE_TESTE,
            defaults={'message_text': request.POST.get('template_teste', '').strip()},
        )

        if request.POST.get('send_test') == '1':
            selected_rows = []
            for row in rows:
                user = row['user']
                if request.POST.get(f'u{user.pk}_send_test'):
                    selected_rows.append(row)
            if not selected_rows:
                messages.error(request, 'Marque pelo menos um contato na coluna Teste para enviar.')
                context = {
                    'rows': self._users_context(),
                    'queue': queue_stats(),
                    'cadastro_template': get_template_message(WhatsAppTemplate.TYPE_CADASTRO),
                    'teste_template': get_template_message(WhatsAppTemplate.TYPE_TESTE),
                }
                context.update(_sidebar_context(request))
                return render(request, self.template_name, context)

            sent_count = 0
            failed_count = 0
            failed_items = []
            for row in selected_rows:
                user = row['user']
                pref = row['pref']
                phone_number = normalize_phone_number(pref.phone_number or resolve_user_phone(user))
                if not phone_number:
                    failed_count += 1
                    failed_items.append(f'{user.username}: telefone ausente/invalido')
                    continue

                queue_item = WhatsAppQueue.objects.create(
                    user=user,
                    phone_number=phone_number,
                    notification_type=WhatsAppQueue.TYPE_TESTE,
                    message_text=get_template_message(WhatsAppTemplate.TYPE_TESTE),
                    status=WhatsAppQueue.STATUS_PENDING,
                )
                success, provider_id, error_message = send_wapi_text(
                    queue_item.phone_number,
                    queue_item.message_text,
                )
                queue_item.attempts = 1
                if success:
                    queue_item.status = WhatsAppQueue.STATUS_SENT
                    queue_item.provider_message_id = provider_id
                    queue_item.sent_at = timezone.now()
                    queue_item.last_error = ''
                    sent_count += 1
                else:
                    queue_item.status = WhatsAppQueue.STATUS_FAILED
                    queue_item.last_error = error_message
                    failed_count += 1
                    failed_items.append(f'{user.username}: {error_message[:80]}')
                queue_item.save(
                    update_fields=[
                        'status',
                        'attempts',
                        'provider_message_id',
                        'sent_at',
                        'last_error',
                    ]
                )
            messages.success(
                request,
                f'Preferencias salvas. Testes enviados: {sent_count}. Falhas: {failed_count}.',
            )
            if failed_items:
                messages.error(request, 'Falhas: ' + ' | '.join(failed_items[:3]))
        else:
            messages.success(request, 'Preferencias de notificacao salvas com sucesso.')

        if cadastro_enabled:
            preview = ', '.join(cadastro_enabled[:6])
            suffix = '...' if len(cadastro_enabled) > 6 else ''
            messages.info(
                request,
                f'Cadastro marcado para: {preview}{suffix}',
            )
        else:
            messages.info(request, 'Nenhum contato esta marcado para receber notificacao de Cadastro.')

        context = {
            'rows': self._users_context(),
            'queue': queue_stats(),
            'cadastro_template': get_template_message(WhatsAppTemplate.TYPE_CADASTRO),
            'teste_template': get_template_message(WhatsAppTemplate.TYPE_TESTE),
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class UsuarioDetalheView(LoginRequiredMixin, View):
    template_name = 'usuario_detalhe.html'

    def get(self, request, pk):
        if not _is_diretor(request.user):
            messages.error(request, 'Seu perfil não possui permissão para acessar usuários.')
            return redirect('accounts:painel')
        target_user = get_object_or_404(User, pk=pk)
        access = _ensure_user_access(target_user)
        display = _user_display_data(target_user)
        responsavel = getattr(target_user, 'responsavel', None)
        diretoria = getattr(target_user, 'diretoria', None)
        aventureiros = responsavel.aventures.order_by('nome') if responsavel else []
        context = {
            'target_user': target_user,
            'access': access,
            'nome_completo': display['nome_completo'],
            'foto_url': display['foto_url'],
            'responsavel': responsavel,
            'diretoria': diretoria,
            'aventureiros': aventureiros,
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class UsuarioPermissaoEditarView(LoginRequiredMixin, View):
    template_name = 'usuario_permissoes_editar.html'

    def get(self, request, pk):
        if not _is_diretor(request.user):
            messages.error(request, 'Seu perfil não possui permissão para editar usuários.')
            return redirect('accounts:painel')
        target_user = get_object_or_404(User, pk=pk)
        access = _ensure_user_access(target_user)
        display = _user_display_data(target_user)
        profiles = list(access.profiles or [])
        if not profiles and access.role:
            profiles = [access.role]
        form = UserAccessForm(initial={'profiles': profiles, 'is_active': target_user.is_active})
        context = {
            'form': form,
            'target_user': target_user,
            'nome_completo': display['nome_completo'],
            'foto_url': display['foto_url'],
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)

    def post(self, request, pk):
        if not _is_diretor(request.user):
            messages.error(request, 'Seu perfil não possui permissão para editar usuários.')
            return redirect('accounts:painel')
        target_user = get_object_or_404(User, pk=pk)
        access = _ensure_user_access(target_user)
        display = _user_display_data(target_user)
        form = UserAccessForm(request.POST)
        if form.is_valid():
            profiles = list(dict.fromkeys(form.cleaned_data['profiles']))
            access.profiles = profiles
            if UserAccess.ROLE_DIRETOR in profiles:
                access.role = UserAccess.ROLE_DIRETOR
            elif UserAccess.ROLE_DIRETORIA in profiles:
                access.role = UserAccess.ROLE_DIRETORIA
            else:
                access.role = UserAccess.ROLE_RESPONSAVEL
            access.save(update_fields=['role', 'profiles', 'updated_at'])
            target_user.is_active = form.cleaned_data['is_active']
            target_user.save(update_fields=['is_active'])
            messages.success(request, 'Permissões atualizadas com sucesso.')
            return redirect('accounts:usuarios')
        context = {
            'form': form,
            'target_user': target_user,
            'nome_completo': display['nome_completo'],
            'foto_url': display['foto_url'],
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)
