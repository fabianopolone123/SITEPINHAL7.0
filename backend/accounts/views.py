import copy
import json
import os

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
    DocumentoTemplate,
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
from django.http import HttpResponse
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
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




def _document_fields():
    return {
        DocumentoTemplate.TYPE_RESPONSAVEL: [
            ('responsavel_nome', 'Responsavel - Nome', 'text'),
            ('responsavel_cpf', 'Responsavel - CPF', 'text'),
            ('responsavel_email', 'Responsavel - E-mail', 'text'),
            ('responsavel_telefone', 'Responsavel - Telefone', 'text'),
            ('responsavel_celular', 'Responsavel - WhatsApp', 'text'),
            ('pai_nome', 'Pai - Nome', 'text'),
            ('pai_email', 'Pai - E-mail', 'text'),
            ('pai_celular', 'Pai - WhatsApp', 'text'),
            ('mae_nome', 'Mae - Nome', 'text'),
            ('mae_email', 'Mae - E-mail', 'text'),
            ('mae_celular', 'Mae - WhatsApp', 'text'),
            ('endereco', 'Endereco - Rua/Numero/Compl.', 'text'),
            ('bairro', 'Endereco - Bairro', 'text'),
            ('cidade', 'Endereco - Cidade', 'text'),
            ('cep', 'Endereco - CEP', 'text'),
            ('estado', 'Endereco - Estado', 'text'),
            ('assinatura', 'Assinatura do responsavel', 'image'),
        ],
        DocumentoTemplate.TYPE_AVENTUREIRO: [
            ('nome', 'Aventureiro - Nome completo', 'text'),
            ('sexo', 'Aventureiro - Sexo', 'text'),
            ('nascimento', 'Aventureiro - Data de nascimento', 'text'),
            ('colegio', 'Aventureiro - Colegio', 'text'),
            ('serie', 'Aventureiro - Serie', 'text'),
            ('bolsa', 'Aventureiro - Bolsa Familia', 'text'),
            ('classes', 'Aventureiro - Classes investidas (nao salvo)', 'text'),
            ('religiao', 'Aventureiro - Religiao', 'text'),
            ('certidao', 'Documentos - Certidao', 'text'),
            ('rg', 'Documentos - RG', 'text'),
            ('orgao', 'Documentos - Orgao expedidor', 'text'),
            ('cpf', 'Documentos - CPF', 'text'),
            ('camiseta', 'Aventureiro - Camiseta', 'text'),
            ('plano', 'Saude - Plano', 'text'),
            ('plano_nome', 'Saude - Nome do plano', 'text'),
            ('tipo_sangue', 'Saude - Tipo sanguineo', 'text'),
            ('alergias', 'Saude - Alergias (resumo)', 'text'),
            ('condicoes', 'Saude - Condicoes (resumo)', 'text'),
            ('foto', 'Foto 3x4 do aventureiro', 'image'),
            ('assinatura', 'Assinatura do aventureiro', 'image'),
        ],
        DocumentoTemplate.TYPE_DIRETORIA: [
            ('nome', 'Diretoria - Nome', 'text'),
            ('igreja', 'Diretoria - Igreja', 'text'),
            ('endereco', 'Diretoria - Endereco', 'text'),
            ('distrito', 'Diretoria - Distrito', 'text'),
            ('numero', 'Diretoria - Numero', 'text'),
            ('bairro', 'Diretoria - Bairro', 'text'),
            ('cep', 'Diretoria - CEP', 'text'),
            ('cidade', 'Diretoria - Cidade', 'text'),
            ('estado', 'Diretoria - Estado', 'text'),
            ('email', 'Diretoria - E-mail', 'text'),
            ('whatsapp', 'Diretoria - WhatsApp', 'text'),
            ('telefone_residencial', 'Diretoria - Tel. residencial', 'text'),
            ('telefone_comercial', 'Diretoria - Tel. comercial', 'text'),
            ('nascimento', 'Diretoria - Nascimento', 'text'),
            ('estado_civil', 'Diretoria - Estado civil', 'text'),
            ('cpf', 'Diretoria - CPF', 'text'),
            ('rg', 'Diretoria - RG', 'text'),
            ('conjuge', 'Diretoria - Conjuge', 'text'),
            ('filho_1', 'Diretoria - Filho(a) 1', 'text'),
            ('filho_2', 'Diretoria - Filho(a) 2', 'text'),
            ('filho_3', 'Diretoria - Filho(a) 3', 'text'),
            ('foto', 'Foto 3x4 da diretoria', 'image'),
            ('assinatura', 'Assinatura da diretoria', 'image'),
        ],
    }


def _combined_document_fields():
    fields = []
    seen = set()
    for group in _document_fields().values():
        for key, label, field_type in group:
            if key in seen:
                continue
            seen.add(key)
            fields.append((key, label, field_type))
    return fields


def _document_field_groups():
    def pick(keys):
        mapping = {}
        for group in _document_fields().values():
            for key, label, field_type in group:
                mapping[key] = (key, label, field_type)
        return [mapping[k] for k in keys if k in mapping]

    groups = [
        ('Aventureiro', pick([
            'nome', 'sexo', 'nascimento', 'colegio', 'serie', 'bolsa', 'religiao',
            'camiseta', 'tipo_sangue', 'plano', 'plano_nome',
        ])),
        ('Documentos', pick(['certidao', 'rg', 'orgao', 'cpf'])),
        ('Responsavel', pick([
            'responsavel_nome', 'responsavel_cpf', 'responsavel_email',
            'responsavel_telefone', 'responsavel_celular',
        ])),
        ('Pai', pick(['pai_nome', 'pai_email', 'pai_celular'])),
        ('Mae', pick(['mae_nome', 'mae_email', 'mae_celular'])),
        ('Endereco', pick(['endereco', 'bairro', 'cidade', 'cep', 'estado'])),
        ('Saude (Resumo)', pick(['alergias', 'condicoes'])),
        ('Imagens', pick(['foto', 'assinatura'])),
        ('Diretoria', pick([
            'nome', 'igreja', 'email', 'whatsapp',
            'endereco', 'bairro', 'cidade', 'cep', 'estado',
            'assinatura',
        ])),
    ]
    # Remove empty groups.
    return [{'title': title, 'items': items} for (title, items) in groups if items]


def _collect_responsavel_data(responsavel):
    return {
        'responsavel_nome': responsavel.responsavel_nome,
        'responsavel_cpf': responsavel.responsavel_cpf,
        'responsavel_email': responsavel.responsavel_email,
        'responsavel_telefone': responsavel.responsavel_telefone,
        'responsavel_celular': responsavel.responsavel_celular,
        'pai_nome': responsavel.pai_nome,
        'pai_email': responsavel.pai_email,
        'mae_nome': responsavel.mae_nome,
        'mae_email': responsavel.mae_email,
        'pai_celular': responsavel.pai_celular,
        'mae_celular': responsavel.mae_celular,
        'endereco': responsavel.endereco,
        'bairro': responsavel.bairro,
        'cidade': responsavel.cidade,
        'cep': responsavel.cep,
        'estado': responsavel.estado,
        'assinatura': responsavel.signature.path if responsavel.signature else '',
    }


def _collect_aventureiro_data(aventureiro):
    responsavel = aventureiro.responsavel
    condicoes = aventureiro.condicoes or {}
    alergias = aventureiro.alergias or {}
    condicoes_resumo = []
    for key, info in condicoes.items():
        if info.get('resposta') == 'sim':
            condicoes_resumo.append(f"{key}: {info.get('detalhe') or ''}".strip())
    alergias_resumo = []
    for key, info in alergias.items():
        if info.get('resposta') == 'sim':
            alergias_resumo.append(f"{key}: {info.get('descricao') or ''}".strip())

    return {
        'nome': aventureiro.nome,
        'sexo': aventureiro.sexo,
        'nascimento': aventureiro.nascimento.strftime('%d/%m/%Y') if aventureiro.nascimento else '',
        'colegio': aventureiro.colegio,
        'serie': aventureiro.serie,
        'bolsa': aventureiro.bolsa,
        'classes': '',
        'religiao': aventureiro.religiao,
        'certidao': aventureiro.certidao,
        'rg': aventureiro.rg,
        'orgao': aventureiro.orgao,
        'cpf': aventureiro.cpf,
        'camiseta': aventureiro.camiseta,
        'plano': aventureiro.plano,
        'plano_nome': aventureiro.plano_nome,
        'tipo_sangue': aventureiro.tipo_sangue,
        'endereco': responsavel.endereco,
        'bairro': responsavel.bairro,
        'cidade': responsavel.cidade,
        'cep': responsavel.cep,
        'estado': responsavel.estado,
        'responsavel_nome': responsavel.responsavel_nome or responsavel.mae_nome or responsavel.pai_nome,
        'responsavel_celular': responsavel.responsavel_celular,
        'pai_celular': responsavel.pai_celular,
        'mae_celular': responsavel.mae_celular,
        'alergias': '; '.join(alergias_resumo),
        'condicoes': '; '.join(condicoes_resumo),
        'foto': aventureiro.foto.path if aventureiro.foto else '',
        'assinatura': aventureiro.assinatura.path if aventureiro.assinatura else '',
    }


def _collect_diretoria_data(diretoria):
    return {
        'nome': diretoria.nome,
        'igreja': diretoria.igreja,
        'endereco': diretoria.endereco,
        'distrito': diretoria.distrito,
        'numero': diretoria.numero,
        'bairro': diretoria.bairro,
        'cep': diretoria.cep,
        'cidade': diretoria.cidade,
        'estado': diretoria.estado,
        'email': diretoria.email,
        'whatsapp': diretoria.whatsapp,
        'telefone_residencial': diretoria.telefone_residencial,
        'telefone_comercial': diretoria.telefone_comercial,
        'nascimento': diretoria.nascimento.strftime('%d/%m/%Y') if diretoria.nascimento else '',
        'estado_civil': diretoria.estado_civil,
        'cpf': diretoria.cpf,
        'rg': diretoria.rg,
        'conjuge': diretoria.conjuge,
        'filho_1': diretoria.filho_1,
        'filho_2': diretoria.filho_2,
        'filho_3': diretoria.filho_3,
        'foto': diretoria.foto.path if diretoria.foto else '',
        'assinatura': diretoria.assinatura.path if diretoria.assinatura else '',
    }




def _load_document_font(size):
    candidates = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'ui', 'static', 'fonts', 'DejaVuSans.ttf'),
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _render_document_image(template, data):
    background_path = template.background.path
    img = Image.open(background_path).convert('RGBA')
    draw = ImageDraw.Draw(img)
    base_font = _load_document_font(18)

    for item in template.positions or []:
        key = item.get('key')
        field_type = item.get('type', 'text')
        x = int(item.get('x', 0))
        y = int(item.get('y', 0))
        w = int(item.get('w', 0) or 0)
        h = int(item.get('h', 0) or 0)
        font_size = int(item.get('font_size', 18) or 18)
        if field_type == 'image':
            path = data.get(key) or ''
            if not path:
                continue
            try:
                stamp = Image.open(path).convert('RGBA')
            except OSError:
                continue
            if w > 0 and h > 0:
                # Preserve aspect ratio inside the target box.
                stamp.thumbnail((w, h))
                paste_x = x + max((w - stamp.width) // 2, 0)
                paste_y = y + max((h - stamp.height) // 2, 0)
            else:
                paste_x = x
                paste_y = y
            img.paste(stamp, (paste_x, paste_y), stamp)
        else:
            value = data.get(key) or ''
            if not value:
                continue
            font = _load_document_font(font_size) or base_font
            draw.text((x, y), str(value), fill=(15, 23, 42), font=font)

    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return output

def _set_pending_aventures(session, pending):
    session['aventures_pending'] = pending
    session.modified = True


def _clear_pending_aventures(session):
    _set_pending_aventures(session, [])


def _pending_count(session):
    return len(_get_pending_aventures(session))


def _required_field_names(form):
    names = list(getattr(form, 'required_display_fields', []) or [])
    for name, field in form.fields.items():
        widget = getattr(field, 'widget', None)
        input_type = getattr(widget, 'input_type', '')
        if field.required and input_type != 'hidden':
            names.append(name)
    deduped = []
    seen = set()
    for item in names:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


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
        # Usa o fuso configurado do Django (America/Sao_Paulo) ao montar a mensagem.
        'data_hora': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M'),
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
        return render(request, self.template_name, {
            'form': form,
            'required_fields': _required_field_names(form),
        })

    def post(self, request):
        form = ResponsavelForm(request.POST)
        if form.is_valid():
            responsavel = form.save()
            login(request, responsavel.user)
            messages.success(request, 'Responsável cadastrado com sucesso. Continue com a ficha do aventureiro.')
            return redirect('accounts:aventura')
        messages.error(request, 'Há campos obrigatórios pendentes; corrija e envie novamente.')
        return render(request, self.template_name, {
            'form': form,
            'required_fields': _required_field_names(form),
        })


class DiretoriaView(View):
    template_name = 'diretoria.html'

    def get(self, request):
        form = DiretoriaForm()
        return render(request, self.template_name, {
            'form': form,
            'required_fields': _required_field_names(form),
        })

    def post(self, request):
        form = DiretoriaForm(request.POST)
        if form.is_valid():
            diretoria = form.save()
            _dispatch_cadastro_notifications('Diretoria', diretoria.user, diretoria.nome)
            messages.success(request, 'Cadastro da diretoria concluído com sucesso. Faça login para continuar.')
            return redirect('accounts:login')
        messages.error(request, 'Há campos obrigatórios pendentes; corrija e envie novamente.')
        return render(request, self.template_name, {
            'form': form,
            'required_fields': _required_field_names(form),
        })


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
            'required_fields': _required_field_names(form),
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




class DocumentosInscricaoView(LoginRequiredMixin, View):
    template_name = 'documentos_inscricao.html'

    def _guard(self, request):
        if not _is_diretor(request.user):
            messages.error(request, 'Seu perfil n?o possui permiss?o para acessar documentos.')
            return redirect('accounts:painel')
        return None

    def get(self, request):
        guard = self._guard(request)
        if guard:
            return guard
        templates = DocumentoTemplate.objects.order_by('name')
        responsaveis = Responsavel.objects.select_related('user').order_by('user__username')
        aventureiros = Aventureiro.objects.select_related('responsavel', 'responsavel__user').order_by('nome')
        diretorias = Diretoria.objects.select_related('user').order_by('user__username')
        selected_id = request.GET.get('template')
        selected = None
        fields = []
        if selected_id:
            selected = DocumentoTemplate.objects.filter(pk=selected_id).first()
            if selected:
                fields = _document_field_groups()
        context = {
            'templates': templates,
            'responsaveis': responsaveis,
            'aventureiros': aventureiros,
            'diretorias': diretorias,
            'selected_template': selected,
            'selected_positions': (selected.positions if selected else []) or [],
            'selected_positions_json': json.dumps((selected.positions if selected else []) or []),
            'fields': fields,
            'template_types': DocumentoTemplate.TYPE_CHOICES,
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)

    def post(self, request):
        guard = self._guard(request)
        if guard:
            return guard
        action = request.POST.get('action')
        if action == 'create_template':
            name = request.POST.get('name', '').strip()
            template_type = request.POST.get('template_type')
            background = request.FILES.get('background')
            if not (name and template_type and background):
                messages.error(request, 'Preencha nome, tipo e imagem do template.')
            else:
                template = DocumentoTemplate.objects.create(
                    name=name,
                    template_type=template_type,
                    background=background,
                )
                messages.success(request, 'Template criado. Ajuste as posi??es e salve.')
                return redirect(f"{request.path}?template={template.pk}")
        elif action == 'save_positions':
            template_id = request.POST.get('template_id')
            template = DocumentoTemplate.objects.filter(pk=template_id).first()
            if not template:
                messages.error(request, 'Template n?o encontrado.')
                return redirect(request.path)
            positions_raw = request.POST.get('positions_json', '[]')
            try:
                positions = json.loads(positions_raw)
            except json.JSONDecodeError:
                messages.error(request, 'N?o foi poss?vel salvar as posi??es.')
            else:
                template.positions = positions
                template.save(update_fields=['positions', 'updated_at'])
                messages.success(request, 'Posi??es salvas com sucesso.')
                return redirect(f"{request.path}?template={template.pk}")
        elif action == 'delete_template':
            template_id = request.POST.get('template_id')
            template = DocumentoTemplate.objects.filter(pk=template_id).first()
            if not template:
                messages.error(request, 'Template não encontrado.')
                return redirect(request.path)
            # Remove the uploaded background file as well.
            if template.background:
                template.background.delete(save=False)
            template.delete()
            messages.success(request, 'Template apagado com sucesso.')
            return redirect(request.path)
        return redirect(request.path)


class DocumentoGerarView(LoginRequiredMixin, View):
    def get(self, request, template_id, kind, pk):
        if not _is_diretor(request.user):
            messages.error(request, 'Seu perfil n?o possui permiss?o para gerar documentos.')
            return redirect('accounts:painel')
        template = get_object_or_404(DocumentoTemplate, pk=template_id)
        if kind == DocumentoTemplate.TYPE_RESPONSAVEL:
            responsavel = get_object_or_404(Responsavel, pk=pk)
            data = _collect_responsavel_data(responsavel)
        elif kind == DocumentoTemplate.TYPE_DIRETORIA:
            diretoria = get_object_or_404(Diretoria, pk=pk)
            data = _collect_diretoria_data(diretoria)
        else:
            aventureiro = get_object_or_404(Aventureiro, pk=pk)
            data = _collect_aventureiro_data(aventureiro)

        output = _render_document_image(template, data)
        response = HttpResponse(output.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="documento_{pk}.png"'
        return response


class WhatsAppView(LoginRequiredMixin, View):
    template_name = 'whatsapp.html'

    def _director_guard(self, request):
        if not _is_diretor(request.user):
            messages.error(request, 'Seu perfil não possui permissão para acessar WhatsApp.')
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
                f'Preferências salvas. Testes enviados: {sent_count}. Falhas: {failed_count}.',
            )
            if failed_items:
                messages.error(request, 'Falhas: ' + ' | '.join(failed_items[:3]))
        else:
            messages.success(request, 'Preferências de notificação salvas com sucesso.')

        if cadastro_enabled:
            preview = ', '.join(cadastro_enabled[:6])
            suffix = '...' if len(cadastro_enabled) > 6 else ''
            messages.info(
                request,
                f'Cadastro marcado para: {preview}{suffix}',
            )
        else:
            messages.info(request, 'Nenhum contato está marcado para receber notificação de Cadastro.')

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
