import copy

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

from .forms import (
    ResponsavelForm,
    DiretoriaForm,
    AventureiroForm,
    ResponsavelDadosForm,
    AventureiroDadosForm,
)
from .models import Responsavel, Aventureiro, Diretoria
from .utils import decode_signature, decode_photo
from datetime import date


def _get_pending_aventures(session):
    return session.get('aventures_pending', [])


def _set_pending_aventures(session, pending):
    session['aventures_pending'] = pending
    session.modified = True


def _clear_pending_aventures(session):
    _set_pending_aventures(session, [])


def _pending_count(session):
    return len(_get_pending_aventures(session))


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
            login(request, diretoria.user)
            messages.success(request, 'Cadastro da diretoria concluído com sucesso.')
            return redirect('accounts:painel')
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
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        aventureiros = responsavel.aventures.order_by('nome')
        context = {
            'responsavel': responsavel,
            'aventureiros': aventureiros,
        }
        return render(request, self.template_name, context)


class MeuResponsavelDetalheView(LoginRequiredMixin, View):
    template_name = 'meus_dados_responsavel.html'

    def get(self, request):
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        return render(request, self.template_name, {'responsavel': responsavel})


class MeuResponsavelEditarView(LoginRequiredMixin, View):
    template_name = 'meus_dados_responsavel_editar.html'

    def get(self, request):
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        form = ResponsavelDadosForm(instance=responsavel)
        return render(request, self.template_name, {'form': form})

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
        return render(request, self.template_name, {'form': form})


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
        }
        return render(request, self.template_name, context)


class MeuAventureiroEditarView(LoginRequiredMixin, View):
    template_name = 'meus_dados_aventureiro_editar.html'

    def get(self, request, pk):
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        aventureiro = get_object_or_404(Aventureiro, pk=pk, responsavel=responsavel)
        form = AventureiroDadosForm(instance=aventureiro)
        return render(request, self.template_name, {'form': form, 'aventureiro': aventureiro})

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
        return render(request, self.template_name, {'form': form, 'aventureiro': aventureiro})
