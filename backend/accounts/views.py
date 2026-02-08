import copy
import json
import os
import re

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
    NovoCadastroLoginForm,
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
    AventureiroFicha,
    DiretoriaFicha,
    AccessGroup,
    DocumentoInscricaoGerado,
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
from django.http import HttpResponse, JsonResponse
from django.db import IntegrityError, transaction
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import date

User = get_user_model()

MENU_ITEMS = [
    ('inicio', 'Início'),
    ('meus_dados', 'Meus dados'),
    ('aventureiros', 'Aventureiros'),
    ('usuarios', 'Usuários'),
    ('whatsapp', 'WhatsApp'),
    ('documentos_inscricao', 'Documentos inscrição'),
    ('permissoes', 'Permissões'),
]

MENU_KEYS = {item[0] for item in MENU_ITEMS}


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


def _normalize_menu_keys(values):
    current = set()
    for item in values or []:
        key = str(item or '').strip()
        if key in MENU_KEYS:
            current.add(key)
    return sorted(current)


def _effective_menu_permissions(user):
    access = _ensure_user_access(user)
    user_override = _normalize_menu_keys(access.menu_allow)
    if user_override:
        return user_override

    allowed = {'inicio', 'meus_dados'}
    profiles = set(access.profiles or [])
    if access.role:
        profiles.add(access.role)
    if UserAccess.ROLE_DIRETOR in profiles:
        allowed.update({'aventureiros', 'usuarios', 'whatsapp', 'documentos_inscricao', 'permissoes'})
    for group in user.access_groups.all():
        allowed.update(_normalize_menu_keys(group.menu_permissions))
    return sorted(allowed)


def _has_menu_permission(user, menu_key):
    return menu_key in _effective_menu_permissions(user)


def _sidebar_context(request):
    access = _ensure_user_access(request.user)
    return {
        'is_diretor': access.has_profile(UserAccess.ROLE_DIRETOR),
        'current_profiles': access.get_profiles_display(),
        'menu_permissions': _effective_menu_permissions(request.user),
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


def _require_menu_or_redirect(request, menu_key, message):
    if not _has_menu_permission(request.user, menu_key):
        messages.error(request, message)
        return redirect('accounts:painel')
    return None


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


def _ensure_default_access_groups():
    defaults = [
        ('diretor', 'Diretor', ['inicio', 'meus_dados', 'aventureiros', 'usuarios', 'whatsapp', 'documentos_inscricao', 'permissoes']),
        ('responsavel', 'Responsavel', ['inicio', 'meus_dados']),
        ('professor', 'Professor', ['inicio', 'meus_dados']),
    ]
    for code, name, menus in defaults:
        group, _ = AccessGroup.objects.get_or_create(
            code=code,
            defaults={'name': name, 'menu_permissions': menus},
        )
        if not group.menu_permissions:
            group.menu_permissions = menus
            group.save(update_fields=['menu_permissions', 'updated_at'])


def _default_group_codes_for_access(access):
    profiles = set(access.profiles or [])
    if access.role:
        profiles.add(access.role)
    codes = set()
    if UserAccess.ROLE_DIRETOR in profiles:
        codes.add('diretor')
    if UserAccess.ROLE_DIRETORIA in profiles:
        codes.add('diretor')
    if UserAccess.ROLE_RESPONSAVEL in profiles:
        codes.add('responsavel')
    if UserAccess.ROLE_PROFESSOR in profiles:
        codes.add('professor')
    return codes




def _document_fields():
    # Important: keys must be unique across all groups, otherwise the palette grouping
    # and the saved positions will collide (e.g. "nome" exists for diretoria and aventureiro).
    return {
        DocumentoTemplate.TYPE_RESPONSAVEL: [
            ('resp_responsavel_nome', 'Responsavel - Nome', 'text'),
            ('resp_responsavel_cpf', 'Responsavel - CPF', 'text'),
            ('resp_responsavel_email', 'Responsavel - E-mail', 'text'),
            ('resp_responsavel_telefone', 'Responsavel - Telefone', 'text'),
            ('resp_responsavel_whatsapp', 'Responsavel - WhatsApp', 'text'),
            ('resp_pai_nome', 'Pai - Nome', 'text'),
            ('resp_pai_email', 'Pai - E-mail', 'text'),
            ('resp_pai_whatsapp', 'Pai - WhatsApp', 'text'),
            ('resp_mae_nome', 'Mae - Nome', 'text'),
            ('resp_mae_email', 'Mae - E-mail', 'text'),
            ('resp_mae_whatsapp', 'Mae - WhatsApp', 'text'),
            ('resp_endereco', 'Endereco - Rua/Numero/Compl.', 'text'),
            ('resp_bairro', 'Endereco - Bairro', 'text'),
            ('resp_cidade', 'Endereco - Cidade', 'text'),
            ('resp_cep', 'Endereco - CEP', 'text'),
            ('resp_estado', 'Endereco - Estado', 'text'),
            ('resp_assinatura', 'Assinatura do responsavel', 'image'),
        ],
        DocumentoTemplate.TYPE_AVENTUREIRO: [
            ('av_nome', 'Aventureiro - Nome completo', 'text'),
            ('av_sexo', 'Aventureiro - Sexo', 'text'),
            ('av_nascimento', 'Aventureiro - Data de nascimento', 'text'),
            ('av_colegio', 'Aventureiro - Colegio', 'text'),
            ('av_serie', 'Aventureiro - Serie', 'text'),
            ('av_bolsa', 'Aventureiro - Bolsa Familia', 'text'),
            ('av_classes', 'Aventureiro - Classes investidas (nao salvo)', 'text'),
            ('av_religiao', 'Aventureiro - Religiao', 'text'),
            ('av_certidao', 'Documentos - Certidao', 'text'),
            ('av_rg', 'Documentos - RG', 'text'),
            ('av_orgao', 'Documentos - Orgao expedidor', 'text'),
            ('av_cpf', 'Documentos - CPF', 'text'),
            ('av_camiseta', 'Aventureiro - Camiseta', 'text'),
            ('av_plano', 'Saude - Plano', 'text'),
            ('av_plano_nome', 'Saude - Nome do plano', 'text'),
            ('av_tipo_sangue', 'Saude - Tipo sanguineo', 'text'),
            ('av_alergias', 'Saude - Alergias (resumo)', 'text'),
            ('av_condicoes', 'Saude - Condicoes (resumo)', 'text'),
            ('av_foto', 'Foto 3x4 do aventureiro', 'image'),
            ('av_assinatura', 'Assinatura do aventureiro', 'image'),
        ],
        DocumentoTemplate.TYPE_DIRETORIA: [
            ('dir_nome', 'Diretoria - Nome', 'text'),
            ('dir_igreja', 'Diretoria - Igreja', 'text'),
            ('dir_endereco', 'Diretoria - Endereco', 'text'),
            ('dir_distrito', 'Diretoria - Distrito', 'text'),
            ('dir_numero', 'Diretoria - Numero', 'text'),
            ('dir_bairro', 'Diretoria - Bairro', 'text'),
            ('dir_cep', 'Diretoria - CEP', 'text'),
            ('dir_cidade', 'Diretoria - Cidade', 'text'),
            ('dir_estado', 'Diretoria - Estado', 'text'),
            ('dir_email', 'Diretoria - E-mail', 'text'),
            ('dir_whatsapp', 'Diretoria - WhatsApp', 'text'),
            ('dir_telefone_residencial', 'Diretoria - Tel. residencial', 'text'),
            ('dir_telefone_comercial', 'Diretoria - Tel. comercial', 'text'),
            ('dir_nascimento', 'Diretoria - Nascimento', 'text'),
            ('dir_estado_civil', 'Diretoria - Estado civil', 'text'),
            ('dir_cpf', 'Diretoria - CPF', 'text'),
            ('dir_rg', 'Diretoria - RG', 'text'),
            ('dir_conjuge', 'Diretoria - Conjuge', 'text'),
            ('dir_filho_1', 'Diretoria - Filho(a) 1', 'text'),
            ('dir_filho_2', 'Diretoria - Filho(a) 2', 'text'),
            ('dir_filho_3', 'Diretoria - Filho(a) 3', 'text'),
            ('dir_foto', 'Foto 3x4 da diretoria', 'image'),
            ('dir_assinatura', 'Assinatura da diretoria', 'image'),
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
    return [
        {
            'title': 'Aventureiro',
            'fields': [
                ('av_nome', 'Aventureiro - Nome completo', 'text'),
                ('av_sexo', 'Aventureiro - Sexo', 'text'),
                ('av_nascimento', 'Aventureiro - Data de nascimento', 'text'),
                ('av_colegio', 'Aventureiro - Colegio', 'text'),
                ('av_serie', 'Aventureiro - Serie', 'text'),
                ('av_bolsa', 'Aventureiro - Bolsa Familia', 'text'),
                ('av_religiao', 'Aventureiro - Religiao', 'text'),
                ('av_camiseta', 'Aventureiro - Camiseta', 'text'),
            ],
        },
        {
            'title': 'Documentos (Aventureiro)',
            'fields': [
                ('av_certidao', 'Documentos - Certidao', 'text'),
                ('av_rg', 'Documentos - RG', 'text'),
                ('av_orgao', 'Documentos - Orgao expedidor', 'text'),
                ('av_cpf', 'Documentos - CPF', 'text'),
            ],
        },
        {
            'title': 'Saude (Aventureiro)',
            'fields': [
                ('av_plano', 'Saude - Plano', 'text'),
                ('av_plano_nome', 'Saude - Nome do plano', 'text'),
                ('av_tipo_sangue', 'Saude - Tipo sanguineo', 'text'),
                ('av_alergias', 'Saude - Alergias (resumo)', 'text'),
                ('av_condicoes', 'Saude - Condicoes (resumo)', 'text'),
            ],
        },
        {
            'title': 'Imagens (Aventureiro)',
            'fields': [
                ('av_foto', 'Foto 3x4 do aventureiro', 'image'),
                ('av_assinatura', 'Assinatura do aventureiro', 'image'),
            ],
        },
        {
            'title': 'Responsavel',
            'fields': [
                ('resp_responsavel_nome', 'Responsavel - Nome', 'text'),
                ('resp_responsavel_cpf', 'Responsavel - CPF', 'text'),
                ('resp_responsavel_email', 'Responsavel - E-mail', 'text'),
                ('resp_responsavel_telefone', 'Responsavel - Telefone', 'text'),
                ('resp_responsavel_whatsapp', 'Responsavel - WhatsApp', 'text'),
                ('resp_assinatura', 'Assinatura do responsavel', 'image'),
            ],
        },
        {
            'title': 'Pai',
            'fields': [
                ('resp_pai_nome', 'Pai - Nome', 'text'),
                ('resp_pai_email', 'Pai - E-mail', 'text'),
                ('resp_pai_whatsapp', 'Pai - WhatsApp', 'text'),
            ],
        },
        {
            'title': 'Mae',
            'fields': [
                ('resp_mae_nome', 'Mae - Nome', 'text'),
                ('resp_mae_email', 'Mae - E-mail', 'text'),
                ('resp_mae_whatsapp', 'Mae - WhatsApp', 'text'),
            ],
        },
        {
            'title': 'Endereco (Responsavel)',
            'fields': [
                ('resp_endereco', 'Endereco - Rua/Numero/Compl.', 'text'),
                ('resp_bairro', 'Endereco - Bairro', 'text'),
                ('resp_cidade', 'Endereco - Cidade', 'text'),
                ('resp_cep', 'Endereco - CEP', 'text'),
                ('resp_estado', 'Endereco - Estado', 'text'),
            ],
        },
        {
            'title': 'Diretoria',
            'fields': [
                ('dir_nome', 'Diretoria - Nome', 'text'),
                ('dir_nascimento', 'Diretoria - Nascimento', 'text'),
                ('dir_email', 'Diretoria - E-mail', 'text'),
                ('dir_whatsapp', 'Diretoria - WhatsApp', 'text'),
                ('dir_foto', 'Foto 3x4 da diretoria', 'image'),
                ('dir_assinatura', 'Assinatura da diretoria', 'image'),
            ],
        },
    ]


def _collect_responsavel_data(responsavel):
    return {
        'resp_responsavel_nome': responsavel.responsavel_nome,
        'resp_responsavel_cpf': responsavel.responsavel_cpf,
        'resp_responsavel_email': responsavel.responsavel_email,
        'resp_responsavel_telefone': responsavel.responsavel_telefone,
        'resp_responsavel_whatsapp': responsavel.responsavel_celular,
        'resp_pai_nome': responsavel.pai_nome,
        'resp_pai_email': responsavel.pai_email,
        'resp_mae_nome': responsavel.mae_nome,
        'resp_mae_email': responsavel.mae_email,
        'resp_pai_whatsapp': responsavel.pai_celular,
        'resp_mae_whatsapp': responsavel.mae_celular,
        'resp_endereco': responsavel.endereco,
        'resp_bairro': responsavel.bairro,
        'resp_cidade': responsavel.cidade,
        'resp_cep': responsavel.cep,
        'resp_estado': responsavel.estado,
        'resp_assinatura': responsavel.signature.path if responsavel.signature else '',
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

    data = {
        'av_nome': aventureiro.nome,
        'av_sexo': aventureiro.sexo,
        'av_nascimento': aventureiro.nascimento.strftime('%d/%m/%Y') if aventureiro.nascimento else '',
        'av_colegio': aventureiro.colegio,
        'av_serie': aventureiro.serie,
        'av_bolsa': aventureiro.bolsa,
        'av_classes': '',
        'av_religiao': aventureiro.religiao,
        'av_certidao': aventureiro.certidao,
        'av_rg': aventureiro.rg,
        'av_orgao': aventureiro.orgao,
        'av_cpf': aventureiro.cpf,
        'av_camiseta': aventureiro.camiseta,
        'av_plano': aventureiro.plano,
        'av_plano_nome': aventureiro.plano_nome,
        'av_tipo_sangue': aventureiro.tipo_sangue,
        'av_alergias': '; '.join(alergias_resumo),
        'av_condicoes': '; '.join(condicoes_resumo),
        'av_foto': aventureiro.foto.path if aventureiro.foto else '',
        'av_assinatura': aventureiro.assinatura.path if aventureiro.assinatura else '',
    }
    data.update(_collect_responsavel_data(responsavel))
    return data


def _collect_diretoria_data(diretoria):
    return {
        'dir_nome': diretoria.nome,
        'dir_igreja': diretoria.igreja,
        'dir_endereco': diretoria.endereco,
        'dir_distrito': diretoria.distrito,
        'dir_numero': diretoria.numero,
        'dir_bairro': diretoria.bairro,
        'dir_cep': diretoria.cep,
        'dir_cidade': diretoria.cidade,
        'dir_estado': diretoria.estado,
        'dir_email': diretoria.email,
        'dir_whatsapp': diretoria.whatsapp,
        'dir_telefone_residencial': diretoria.telefone_residencial,
        'dir_telefone_comercial': diretoria.telefone_comercial,
        'dir_nascimento': diretoria.nascimento.strftime('%d/%m/%Y') if diretoria.nascimento else '',
        'dir_estado_civil': diretoria.estado_civil,
        'dir_cpf': diretoria.cpf,
        'dir_rg': diretoria.rg,
        'dir_conjuge': diretoria.conjuge,
        'dir_filho_1': diretoria.filho_1,
        'dir_filho_2': diretoria.filho_2,
        'dir_filho_3': diretoria.filho_3,
        'dir_foto': diretoria.foto.path if diretoria.foto else '',
        'dir_assinatura': diretoria.assinatura.path if diretoria.assinatura else '',
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

    def resolve_value(item_key, item_label, item_type):
        if item_key in data:
            return data.get(item_key) or ''

        # Backward compatibility for older templates that used non-namespaced keys.
        label = (item_label or '').lower()
        key = (item_key or '').lower()
        if key in ('nome', 'sexo', 'nascimento', 'colegio', 'serie', 'bolsa', 'religiao', 'camiseta'):
            return data.get('av_' + key, '') or ''
        if key in ('certidao', 'rg', 'orgao', 'cpf'):
            return data.get('av_' + key, '') or ''
        if key in ('plano', 'plano_nome', 'tipo_sangue', 'alergias', 'condicoes'):
            return data.get('av_' + key, '') or ''
        if key == 'foto':
            return data.get('av_foto', '') or data.get('dir_foto', '') or ''
        if key == 'assinatura':
            # Try to infer by label.
            if 'diretoria' in label:
                return data.get('dir_assinatura', '') or ''
            if 'aventureiro' in label:
                return data.get('av_assinatura', '') or ''
            return data.get('resp_assinatura', '') or ''

        # Legacy directoria fields
        if 'diretoria' in label:
            mapping = {
                'email': 'dir_email',
                'whatsapp': 'dir_whatsapp',
                'endereco': 'dir_endereco',
                'bairro': 'dir_bairro',
                'cidade': 'dir_cidade',
                'cep': 'dir_cep',
                'estado': 'dir_estado',
                'nascimento': 'dir_nascimento',
            }
            if key in mapping:
                return data.get(mapping[key], '') or ''

        # Legacy responsavel fields
        if 'responsavel' in label:
            mapping = {
                'email': 'resp_responsavel_email',
                'telefone': 'resp_responsavel_telefone',
                'celular': 'resp_responsavel_whatsapp',
                'whatsapp': 'resp_responsavel_whatsapp',
                'cpf': 'resp_responsavel_cpf',
                'nome': 'resp_responsavel_nome',
            }
            if key in mapping:
                return data.get(mapping[key], '') or ''

        return ''

    for item in template.positions or []:
        key = item.get('key')
        field_type = item.get('type', 'text')
        x = int(item.get('x', 0))
        y = int(item.get('y', 0))
        w = int(item.get('w', 0) or 0)
        h = int(item.get('h', 0) or 0)
        font_size = int(item.get('font_size', 18) or 18)
        if field_type == 'image':
            path = resolve_value(key, item.get('label'), field_type) or ''
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
            value = resolve_value(key, item.get('label'), field_type) or ''
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
    tipo_lower = str(tipo_cadastro or '').strip().lower()
    if tipo_lower == 'diretoria':
        template_text = get_template_message(WhatsAppTemplate.TYPE_DIRETORIA)
        prefs = WhatsAppPreference.objects.filter(notify_diretoria=True)
        queue_type = WhatsAppQueue.TYPE_DIRETORIA
    else:
        template_text = get_template_message(WhatsAppTemplate.TYPE_CADASTRO)
        prefs = WhatsAppPreference.objects.filter(notify_cadastro=True)
        queue_type = WhatsAppQueue.TYPE_CADASTRO

    for pref in prefs.select_related('user'):
        phone_number = normalize_phone_number(pref.phone_number or resolve_user_phone(pref.user))
        if not phone_number:
            continue
        text = render_message(template_text, payload)
        queue_item = WhatsAppQueue.objects.create(
            user=pref.user,
            phone_number=phone_number,
            notification_type=queue_type,
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


NEW_FLOW_SESSION_KEY = 'novo_cadastro_aventureiro'
NEW_DIRETORIA_FLOW_SESSION_KEY = 'novo_cadastro_diretoria'


def _new_flow_data(session):
    return session.get(NEW_FLOW_SESSION_KEY, {
        'login': {},
        'aventures': [],
    })


def _set_new_flow_data(session, data):
    session[NEW_FLOW_SESSION_KEY] = data
    session.modified = True


def _clear_new_flow(session):
    if NEW_FLOW_SESSION_KEY in session:
        del session[NEW_FLOW_SESSION_KEY]
        session.modified = True


def _new_diretoria_flow_data(session):
    return session.get(NEW_DIRETORIA_FLOW_SESSION_KEY, {'login': {}})


def _set_new_diretoria_flow_data(session, data):
    session[NEW_DIRETORIA_FLOW_SESSION_KEY] = data
    session.modified = True


def _clear_new_diretoria_flow(session):
    if NEW_DIRETORIA_FLOW_SESSION_KEY in session:
        del session[NEW_DIRETORIA_FLOW_SESSION_KEY]
        session.modified = True


def _extract_fields(post, names):
    data = {}
    for name in names:
        values = post.getlist(name)
        if not values:
            data[name] = ''
        elif len(values) == 1:
            data[name] = values[0]
        else:
            data[name] = values
    return data


def _normalize_bool(value):
    return str(value).strip().lower() in {'1', 'true', 'sim', 's', 'on', 'yes'}


def _normalize_cpf(value):
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


def _normalize_doc_text(value):
    raw = str(value or '').upper()
    return re.sub(r'[^A-Z0-9]', '', raw)


def _normalize_inscricao_docs(fields):
    cpf_fields = ['cpf_aventureiro', 'cpf_pai', 'cpf_mae', 'cpf_responsavel']
    for key in cpf_fields:
        if key in fields:
            fields[key] = _normalize_cpf(fields.get(key))
    if 'rg' in fields:
        fields['rg'] = _normalize_doc_text(fields.get('rg'))
    if 'certidao_nascimento' in fields:
        fields['certidao_nascimento'] = _normalize_doc_text(fields.get('certidao_nascimento'))
    return fields


def _find_duplicate_document(field_name, normalized_value):
    value = str(normalized_value or '').strip()
    if not value:
        return None

    if field_name in {'cpf_aventureiro', 'cpf_pai', 'cpf_mae', 'cpf_responsavel'}:
        if Aventureiro.objects.filter(cpf=value).exists():
            return 'CPF já cadastrado em aventureiro.'
        if Diretoria.objects.filter(cpf=value).exists():
            return 'CPF já cadastrado em diretoria.'
        if Responsavel.objects.filter(pai_cpf=value).exists():
            return 'CPF já cadastrado como CPF do pai.'
        if Responsavel.objects.filter(mae_cpf=value).exists():
            return 'CPF já cadastrado como CPF da mãe.'
        if Responsavel.objects.filter(responsavel_cpf=value).exists():
            return 'CPF já cadastrado como CPF do responsável.'
        return None

    if field_name == 'rg':
        if Aventureiro.objects.filter(rg=value).exists():
            return 'RG já cadastrado em aventureiro.'
        if Diretoria.objects.filter(rg=value).exists():
            return 'RG já cadastrado em diretoria.'
        return None

    if field_name == 'certidao_nascimento':
        if Aventureiro.objects.filter(certidao=value).exists():
            return 'Certidão já cadastrada em aventureiro.'
        return None

    return None


def _date_parts_today():
    now = timezone.localtime(timezone.now())
    meses_ptbr = [
        'Janeiro',
        'Fevereiro',
        'Março',
        'Abril',
        'Maio',
        'Junho',
        'Julho',
        'Agosto',
        'Setembro',
        'Outubro',
        'Novembro',
        'Dezembro',
    ]
    return {
        'cidade_data': '',
        'dia_data': f'{now.day:02d}',
        'mes_data': meses_ptbr[now.month - 1],
        'ano_data': str(now.year),
    }


def _normalize_month_pt(value):
    raw = str(value or '').strip()
    if not raw:
        return ''
    normalized = raw.lower()
    mapping = {
        'january': 'Janeiro',
        'february': 'Fevereiro',
        'march': 'Março',
        'april': 'Abril',
        'may': 'Maio',
        'june': 'Junho',
        'july': 'Julho',
        'august': 'Agosto',
        'september': 'Setembro',
        'october': 'Outubro',
        'november': 'Novembro',
        'december': 'Dezembro',
        'janeiro': 'Janeiro',
        'fevereiro': 'Fevereiro',
        'marco': 'Março',
        'março': 'Março',
        'abril': 'Abril',
        'maio': 'Maio',
        'junho': 'Junho',
        'julho': 'Julho',
        'agosto': 'Agosto',
        'setembro': 'Setembro',
        'outubro': 'Outubro',
        'novembro': 'Novembro',
        'dezembro': 'Dezembro',
    }
    return mapping.get(normalized, raw)


def _apply_date_defaults(fields):
    defaults = _date_parts_today()
    for key in ('cidade_data', 'dia_data', 'mes_data', 'ano_data'):
        if not str(fields.get(key, '')).strip():
            fields[key] = defaults[key]
    fields['mes_data'] = _normalize_month_pt(fields.get('mes_data'))
    return fields


def _inscricao_parent_fields_from_last_aventureiro(data):
    aventureiros = data.get('aventures') or []
    if not aventureiros:
        return {}
    last = aventureiros[-1] or {}
    inscricao = last.get('inscricao') or {}
    keys = [
        'nome_pai',
        'email_pai',
        'cpf_pai',
        'tel_pai',
        'cel_pai',
        'nome_mae',
        'email_mae',
        'cpf_mae',
        'tel_mae',
        'cel_mae',
        'nome_responsavel',
        'parentesco',
        'cpf_responsavel',
        'email_responsavel',
        'tel_responsavel',
        'cel_responsavel',
    ]
    return {key: inscricao.get(key, '') for key in keys}


class RegisterView(View):
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name)


class NovoCadastroLoginView(View):
    template_name = 'novo_cadastro/login_inicio.html'

    def get(self, request):
        _clear_new_flow(request.session)
        return render(request, self.template_name, {'form': NovoCadastroLoginForm()})

    def post(self, request):
        form = NovoCadastroLoginForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Corrija os campos para continuar.')
            return render(request, self.template_name, {'form': form})
        data = _new_flow_data(request.session)
        data['login'] = {
            'username': form.cleaned_data['username'].strip(),
            'password': form.cleaned_data['password'],
        }
        _set_new_flow_data(request.session, data)
        return redirect('accounts:novo_cadastro_inscricao')


class NovoCadastroInscricaoView(View):
    template_name = 'novo_cadastro/ficha_inscricao.html'

    field_names = [
        'nome_completo', 'sexo', 'data_nascimento', 'colegio', 'serie', 'bolsa_familia',
        'classes', 'endereco', 'bairro', 'cidade', 'cep', 'estado', 'certidao_nascimento',
        'religiao', 'rg', 'orgao_expedidor', 'cpf_aventureiro', 'tem_whatsapp',
        'tamanho_camiseta', 'nome_pai', 'email_pai', 'cpf_pai', 'tel_pai', 'cel_pai',
        'nome_mae', 'email_mae', 'cpf_mae', 'tel_mae', 'cel_mae', 'nome_responsavel',
        'parentesco', 'cpf_responsavel', 'email_responsavel', 'tel_responsavel',
        'cel_responsavel', 'assinatura_inscricao', 'foto_3x4',
        'cidade_data', 'dia_data', 'mes_data', 'ano_data',
    ]

    def _require_login_step(self, request):
        data = _new_flow_data(request.session)
        if not data.get('login'):
            messages.error(request, 'Comece pelo login do responsável.')
            return None
        return data

    def get(self, request):
        data = self._require_login_step(request)
        if data is None:
            return redirect('accounts:novo_cadastro_login')
        current = data.get('current') or {}
        step_data = current.get('inscricao') or {}
        if not step_data:
            step_data = _inscricao_parent_fields_from_last_aventureiro(data)
        initial = _date_parts_today()
        initial.update(step_data)
        return render(request, self.template_name, {
            'initial': initial,
            'step_data': step_data,
            'has_saved_aventureiros': bool(data.get('aventures')),
        })

    def post(self, request):
        data = self._require_login_step(request)
        if data is None:
            return redirect('accounts:novo_cadastro_login')
        fields = _extract_fields(request.POST, self.field_names)
        _normalize_inscricao_docs(fields)
        _apply_date_defaults(fields)
        duplicate_fields = ['cpf_aventureiro', 'cpf_pai', 'cpf_mae', 'cpf_responsavel', 'rg', 'certidao_nascimento']
        for field_name in duplicate_fields:
            duplicate_message = _find_duplicate_document(field_name, fields.get(field_name))
            if duplicate_message:
                messages.error(request, duplicate_message)
                initial = _date_parts_today()
                initial.update(fields)
                return render(request, self.template_name, {
                    'initial': initial,
                    'step_data': fields,
                    'has_saved_aventureiros': bool(data.get('aventures')),
                })
        required = ['nome_completo', 'data_nascimento', 'nome_responsavel', 'assinatura_inscricao', 'foto_3x4']
        missing = [name for name in required if not str(fields.get(name, '')).strip()]
        if missing:
            messages.error(request, 'Preencha os campos obrigatórios e assine a ficha de inscrição.')
            initial = _date_parts_today()
            initial.update(fields)
            return render(request, self.template_name, {
                'initial': initial,
                'step_data': fields,
                'has_saved_aventureiros': bool(data.get('aventures')),
            })
        if not fields.get('cidade_data'):
            fields['cidade_data'] = fields.get('cidade', '')
        current = {
            'inscricao': fields,
        }
        data['current'] = current
        _set_new_flow_data(request.session, data)
        return redirect('accounts:novo_cadastro_medica')


class VerificarDocumentoView(View):
    def get(self, request):
        field = str(request.GET.get('field', '')).strip()
        value = request.GET.get('value', '')
        if not field:
            return JsonResponse({'ok': False, 'error': 'Campo inválido.'}, status=400)

        if field in {'cpf_aventureiro', 'cpf_pai', 'cpf_mae', 'cpf_responsavel'}:
            normalized = _normalize_cpf(value)
        elif field in {'rg', 'certidao_nascimento'}:
            normalized = _normalize_doc_text(value)
        else:
            return JsonResponse({'ok': False, 'error': 'Campo não suportado.'}, status=400)

        duplicate_message = _find_duplicate_document(field, normalized)
        return JsonResponse({
            'ok': True,
            'field': field,
            'normalized': normalized,
            'duplicate': bool(duplicate_message),
            'message': duplicate_message or '',
        })


class NovoCadastroMedicaView(View):
    template_name = 'novo_cadastro/ficha_medica.html'

    field_names = [
        'plano_saude', 'qual_plano', 'cns_sus', 'doencas', 'alergia_pele', 'alergia_alimentar',
        'alergia_medicamento', 'deficiencia', 'cardiacos', 'cardiacos_medicamentos', 'diabetico',
        'diabetico_medicamentos', 'renais', 'renais_medicamentos', 'psicologicos',
        'psicologicos_medicamentos', 'outros_problemas', 'saude_recente',
        'medicamentos_recentes', 'fraturas', 'cirurgias', 'motivo_internacao', 'tipo_sangue',
    ]

    def _require_inscricao_step(self, request):
        data = _new_flow_data(request.session)
        if not data.get('login'):
            return None
        current = data.get('current') or {}
        if not current.get('inscricao'):
            return None
        return data

    def get(self, request):
        data = self._require_inscricao_step(request)
        if data is None:
            messages.error(request, 'Complete a ficha de inscrição antes.')
            return redirect('accounts:novo_cadastro_inscricao')
        current = data.get('current') or {}
        step_data = current.get('medica') or {}
        return render(request, self.template_name, {'step_data': step_data})

    def post(self, request):
        data = self._require_inscricao_step(request)
        if data is None:
            messages.error(request, 'Complete a ficha de inscrição antes.')
            return redirect('accounts:novo_cadastro_inscricao')
        fields = _extract_fields(request.POST, self.field_names)
        if not str(fields.get('plano_saude', '')).strip():
            messages.error(request, 'Informe se tem plano de saúde para continuar.')
            return render(request, self.template_name, {'step_data': fields})
        required_radios = [
            'cardiacos',
            'diabetico',
            'renais',
            'psicologicos',
            'saude_recente',
            'medicamentos_recentes',
            'fraturas',
            'cirurgias',
            'tipo_sangue',
        ]
        missing = [name for name in required_radios if not str(fields.get(name, '')).strip()]
        if missing:
            messages.error(request, 'Preencha todos os campos obrigatórios de condições de saúde.')
            return render(request, self.template_name, {'step_data': fields})
        data['current']['medica'] = fields
        _set_new_flow_data(request.session, data)
        return redirect('accounts:novo_cadastro_declaracao')


class NovoCadastroDeclaracaoMedicaView(View):
    template_name = 'novo_cadastro/declaracao_medica.html'

    field_names = ['cidade_data', 'dia_data', 'mes_data', 'ano_data', 'assinatura_declaracao_medica']

    def _require_medica_step(self, request):
        data = _new_flow_data(request.session)
        current = data.get('current') or {}
        if not current.get('inscricao') or not current.get('medica'):
            return None
        return data

    def get(self, request):
        data = self._require_medica_step(request)
        if data is None:
            messages.error(request, 'Complete as etapas anteriores.')
            return redirect('accounts:novo_cadastro_inscricao')
        initial = _date_parts_today()
        initial['cidade_data'] = data.get('current', {}).get('inscricao', {}).get('cidade', '')
        return render(request, self.template_name, {'initial': initial, 'step_data': {}})

    def post(self, request):
        data = self._require_medica_step(request)
        if data is None:
            messages.error(request, 'Complete as etapas anteriores.')
            return redirect('accounts:novo_cadastro_inscricao')
        fields = _extract_fields(request.POST, self.field_names)
        if not fields.get('assinatura_declaracao_medica'):
            messages.error(request, 'Assine a declaração médica para continuar.')
            return render(request, self.template_name, {'initial': _date_parts_today(), 'step_data': fields})
        data['current']['declaracao_medica'] = fields
        _set_new_flow_data(request.session, data)
        return redirect('accounts:novo_cadastro_termo')


class NovoCadastroTermoImagemView(View):
    template_name = 'novo_cadastro/termo_imagem.html'

    field_names = [
        'aventureiro_nacionalidade', 'responsavel_nome_termo', 'responsavel_nacionalidade_termo',
        'responsavel_estado_civil_termo', 'responsavel_rg_termo', 'responsavel_cpf_termo',
        'responsavel_endereco_termo', 'responsavel_numero_termo', 'responsavel_cidade_termo',
        'responsavel_estado_termo', 'cidade_data', 'dia_data', 'mes_data', 'ano_data',
        'assinatura_termo_imagem', 'telefone_contato_termo', 'email_contato_termo', 'nome_aventureiro_termo',
    ]

    def _require_declaracao_step(self, request):
        data = _new_flow_data(request.session)
        current = data.get('current') or {}
        if not current.get('inscricao') or not current.get('medica') or not current.get('declaracao_medica'):
            return None
        return data

    def get(self, request):
        data = self._require_declaracao_step(request)
        if data is None:
            messages.error(request, 'Complete as etapas anteriores.')
            return redirect('accounts:novo_cadastro_inscricao')
        inscricao = data.get('current', {}).get('inscricao', {})
        initial = _date_parts_today()
        initial.update({
            'nome_aventureiro_termo': inscricao.get('nome_completo', ''),
            'aventureiro_nacionalidade': 'Brasileiro',
            'responsavel_nome_termo': inscricao.get('nome_responsavel', ''),
            'responsavel_nacionalidade_termo': 'Brasileiro',
            'responsavel_cpf_termo': inscricao.get('cpf_responsavel', ''),
            'responsavel_endereco_termo': inscricao.get('endereco', ''),
            'responsavel_cidade_termo': inscricao.get('cidade', ''),
            'responsavel_estado_termo': inscricao.get('estado', ''),
            'email_contato_termo': inscricao.get('email_responsavel', ''),
            'telefone_contato_termo': inscricao.get('cel_responsavel', ''),
            'cidade_data': inscricao.get('cidade', ''),
        })
        return render(request, self.template_name, {'initial': initial, 'step_data': {}})

    def post(self, request):
        data = self._require_declaracao_step(request)
        if data is None:
            messages.error(request, 'Complete as etapas anteriores.')
            return redirect('accounts:novo_cadastro_inscricao')
        fields = _extract_fields(request.POST, self.field_names)
        if not str(fields.get('aventureiro_nacionalidade', '')).strip():
            fields['aventureiro_nacionalidade'] = 'Brasileiro'
        if not str(fields.get('responsavel_nacionalidade_termo', '')).strip():
            fields['responsavel_nacionalidade_termo'] = 'Brasileiro'
        if not fields.get('assinatura_termo_imagem'):
            messages.error(request, 'Assine o termo de imagem para continuar.')
            initial = _date_parts_today()
            initial.update({
                'aventureiro_nacionalidade': 'Brasileiro',
                'responsavel_nacionalidade_termo': 'Brasileiro',
            })
            return render(request, self.template_name, {'initial': initial, 'step_data': fields})
        data['current']['termo_imagem'] = fields
        _set_new_flow_data(request.session, data)
        return redirect('accounts:novo_cadastro_resumo')


class NovoCadastroResumoView(View):
    template_name = 'novo_cadastro/resumo.html'

    def _is_current_complete(self, data):
        current = data.get('current') or {}
        required_keys = ['inscricao', 'medica', 'declaracao_medica', 'termo_imagem']
        return all(current.get(item) for item in required_keys)

    def _require_access(self, request):
        data = _new_flow_data(request.session)
        aventureiros = data.get('aventures') or []
        if self._is_current_complete(data):
            return data
        if aventureiros:
            # Permite concluir os aventureiros já completos mesmo que a ficha atual esteja incompleta.
            return data
        return None

    def _responsavel_nome(self, data):
        current = data.get('current') or {}
        inscricao = current.get('inscricao') or {}
        if inscricao.get('nome_responsavel'):
            return inscricao.get('nome_responsavel')
        aventureiros = data.get('aventures') or []
        if aventureiros:
            return (aventureiros[0].get('inscricao') or {}).get('nome_responsavel', '')
        return ''

    def get(self, request):
        data = self._require_access(request)
        if data is None:
            return None
            messages.error(request, 'Complete todas as fichas do aventureiro.')
            return redirect('accounts:novo_cadastro_inscricao')
        current = data.get('current', {})
        aventureiros = data.get('aventures', [])
        preview = list(aventureiros)
        current_incomplete = False
        if self._is_current_complete(data):
            preview.append(current)
        elif current:
            current_incomplete = True
        return render(request, self.template_name, {
            'current': current,
            'aventures_preview': preview,
            'responsavel_nome': self._responsavel_nome(data),
            'current_incomplete': current_incomplete,
        })

    def post(self, request):
        action = request.POST.get('action')
        data = self._require_access(request)
        if data is None:
            messages.error(request, 'Complete todas as fichas do aventureiro.')
            return redirect('accounts:novo_cadastro_inscricao')
        if action == 'add_more':
            if self._is_current_complete(data):
                data['aventures'].append(data['current'])
            data['current'] = {}
            _set_new_flow_data(request.session, data)
            messages.success(request, 'Aventureiro salvo temporariamente. Preencha o próximo.')
            return redirect('accounts:novo_cadastro_inscricao')
        if action == 'finalizar':
            if self._is_current_complete(data):
                data['aventures'].append(data['current'])
            elif data.get('current'):
                messages.info(request, 'A ficha atual incompleta foi ignorada. Somente os aventureiros completos foram finalizados.')
            payload = data
            login_data = payload.get('login', {})
            if not login_data:
                messages.error(request, 'Sessão inválida. Reinicie o cadastro.')
                return redirect('accounts:novo_cadastro_login')
            user = User.objects.create_user(
                username=login_data['username'],
                password=login_data['password'],
            )
            access, _ = UserAccess.objects.get_or_create(
                user=user,
                defaults={'role': UserAccess.ROLE_RESPONSAVEL, 'profiles': [UserAccess.ROLE_RESPONSAVEL]},
            )
            access.add_profile(UserAccess.ROLE_RESPONSAVEL)
            access.save(update_fields=['role', 'profiles', 'updated_at'])

            first = payload['aventures'][0]['inscricao']
            responsavel = Responsavel.objects.create(
                user=user,
                pai_nome=first.get('nome_pai', ''),
                pai_cpf=first.get('cpf_pai', ''),
                pai_email=first.get('email_pai', ''),
                pai_telefone=first.get('tel_pai', ''),
                pai_celular=first.get('cel_pai', ''),
                mae_nome=first.get('nome_mae', ''),
                mae_cpf=first.get('cpf_mae', ''),
                mae_email=first.get('email_mae', ''),
                mae_telefone=first.get('tel_mae', ''),
                mae_celular=first.get('cel_mae', ''),
                responsavel_nome=first.get('nome_responsavel', ''),
                responsavel_parentesco=first.get('parentesco', ''),
                responsavel_cpf=first.get('cpf_responsavel', ''),
                responsavel_email=first.get('email_responsavel', ''),
                responsavel_telefone=first.get('tel_responsavel', ''),
                responsavel_celular=first.get('cel_responsavel', ''),
                endereco=first.get('endereco', ''),
                bairro=first.get('bairro', ''),
                cidade=first.get('cidade', ''),
                cep=first.get('cep', ''),
                estado=first.get('estado', ''),
            )
            resp_signature = first.get('assinatura_inscricao')
            if resp_signature:
                signature_file = decode_signature(resp_signature, 'responsavel')
                if signature_file:
                    responsavel.signature.save(signature_file.name, signature_file, save=True)

            for item in payload['aventures']:
                inscricao = item.get('inscricao', {})
                medica = item.get('medica', {})
                declaracao = item.get('declaracao_medica', {})
                termo = item.get('termo_imagem', {})
                condicoes = {
                    'cardiaco': {'resposta': 'sim' if str(medica.get('cardiacos', '')).upper() == 'S' else 'nao', 'detalhe': '', 'medicamento': 'sim' if medica.get('cardiacos_medicamentos') else 'nao', 'remedio': medica.get('cardiacos_medicamentos', '')},
                    'diabetico': {'resposta': 'sim' if str(medica.get('diabetico', '')).upper() == 'S' else 'nao', 'detalhe': '', 'medicamento': 'sim' if medica.get('diabetico_medicamentos') else 'nao', 'remedio': medica.get('diabetico_medicamentos', '')},
                    'renal': {'resposta': 'sim' if str(medica.get('renais', '')).upper() == 'S' else 'nao', 'detalhe': '', 'medicamento': 'sim' if medica.get('renais_medicamentos') else 'nao', 'remedio': medica.get('renais_medicamentos', '')},
                    'psicologico': {'resposta': 'sim' if str(medica.get('psicologicos', '')).upper() == 'S' else 'nao', 'detalhe': '', 'medicamento': 'sim' if medica.get('psicologicos_medicamentos') else 'nao', 'remedio': medica.get('psicologicos_medicamentos', '')},
                }
                alergias = {
                    'alergia_pele': {'resposta': 'sim' if medica.get('alergia_pele') else 'nao', 'descricao': medica.get('alergia_pele', '')},
                    'alergia_alimento': {'resposta': 'sim' if medica.get('alergia_alimentar') else 'nao', 'descricao': medica.get('alergia_alimentar', '')},
                    'alergia_medicamento': {'resposta': 'sim' if medica.get('alergia_medicamento') else 'nao', 'descricao': medica.get('alergia_medicamento', '')},
                }
                try:
                    nascimento = date.fromisoformat(inscricao.get('data_nascimento', ''))
                except ValueError:
                    nascimento = None
                aventureiro = Aventureiro.objects.create(
                    responsavel=responsavel,
                    nome=inscricao.get('nome_completo', ''),
                    sexo='masculino' if inscricao.get('sexo') == 'M' else 'feminino' if inscricao.get('sexo') == 'F' else '',
                    nascimento=nascimento,
                    serie=inscricao.get('serie', ''),
                    colegio=inscricao.get('colegio', ''),
                    bolsa='sim' if inscricao.get('bolsa_familia') == 'sim' else 'nao',
                    religiao=inscricao.get('religiao', ''),
                    certidao=inscricao.get('certidao_nascimento', ''),
                    rg=inscricao.get('rg', ''),
                    orgao=inscricao.get('orgao_expedidor', ''),
                    cpf=inscricao.get('cpf_aventureiro', ''),
                    camiseta=inscricao.get('tamanho_camiseta', ''),
                    plano='sim' if str(medica.get('plano_saude', '')).upper() == 'S' else 'nao',
                    plano_nome=medica.get('qual_plano', ''),
                    cns=medica.get('cns_sus', ''),
                    doencas=medica.get('doencas', []) if isinstance(medica.get('doencas', []), list) else [medica.get('doencas', '')],
                    condicoes=condicoes,
                    alergias=alergias,
                    deficiencias=medica.get('deficiencia', []) if isinstance(medica.get('deficiencia', []), list) else [medica.get('deficiencia', '')],
                    tipo_sangue=medica.get('tipo_sangue', ''),
                    declaracao_medica=True,
                    autorizacao_imagem=True,
                )
                photo_value = inscricao.get('foto_3x4')
                if photo_value:
                    photo = decode_photo(photo_value)
                    if photo:
                        aventureiro.foto.save(photo.name, photo, save=True)

                assinatura_aventureiro = inscricao.get('assinatura_inscricao')
                if assinatura_aventureiro:
                    signature = decode_signature(assinatura_aventureiro, 'aventura')
                    if signature:
                        aventureiro.assinatura.save(signature.name, signature, save=True)

                ficha = AventureiroFicha.objects.create(
                    aventureiro=aventureiro,
                    inscricao_data=inscricao,
                    ficha_medica_data=medica,
                    declaracao_medica_data=declaracao,
                    termo_imagem_data=termo,
                )
                if inscricao.get('assinatura_inscricao'):
                    assinatura = decode_signature(inscricao.get('assinatura_inscricao'), 'ficha_inscricao')
                    if assinatura:
                        ficha.assinatura_inscricao.save(assinatura.name, assinatura, save=False)
                if declaracao.get('assinatura_declaracao_medica'):
                    assinatura = decode_signature(declaracao.get('assinatura_declaracao_medica'), 'declaracao_medica')
                    if assinatura:
                        ficha.assinatura_declaracao_medica.save(assinatura.name, assinatura, save=False)
                if termo.get('assinatura_termo_imagem'):
                    assinatura = decode_signature(termo.get('assinatura_termo_imagem'), 'termo_imagem')
                    if assinatura:
                        ficha.assinatura_termo_imagem.save(assinatura.name, assinatura, save=False)
                ficha.save()

            _dispatch_cadastro_notifications(
                'Cadastro completo',
                user,
                responsavel.responsavel_nome or responsavel.mae_nome or responsavel.pai_nome,
            )
            _clear_new_flow(request.session)
            messages.success(request, 'Cadastro efetuado com sucesso.')
            return redirect('accounts:login')
        return redirect('accounts:novo_cadastro_resumo')


class NovoCadastroDiretoriaLoginView(View):
    template_name = 'novo_diretoria/login_inicio.html'

    def get(self, request):
        _clear_new_diretoria_flow(request.session)
        return render(request, self.template_name, {'form': NovoCadastroLoginForm()})

    def post(self, request):
        form = NovoCadastroLoginForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Corrija os campos para continuar.')
            return render(request, self.template_name, {'form': form})
        data = _new_diretoria_flow_data(request.session)
        data['login'] = {
            'username': form.cleaned_data['username'].strip(),
            'password': form.cleaned_data['password'],
        }
        _set_new_diretoria_flow_data(request.session, data)
        return redirect('accounts:novo_diretoria_compromisso')


class NovoCadastroDiretoriaCompromissoView(View):
    template_name = 'novo_diretoria/compromisso_voluntariado.html'
    field_names = [
        'nome', 'igreja', 'endereco', 'distrito', 'numero', 'bairro', 'cep', 'cidade',
        'estado', 'email', 'whatsapp', 'telefone_residencial', 'telefone_comercial',
        'nascimento', 'estado_civil', 'cpf', 'rg', 'conjuge', 'filho_1', 'filho_2', 'filho_3',
        'possui_limitacao_saude', 'limitacao_saude_descricao', 'escolaridade',
        'declaracao_medica', 'foto_3x4', 'assinatura_compromisso',
    ]

    def _require_login_step(self, request):
        data = _new_diretoria_flow_data(request.session)
        if not data.get('login'):
            messages.error(request, 'Comece pelo login da diretoria.')
            return None
        return data

    def get(self, request):
        data = self._require_login_step(request)
        if data is None:
            return redirect('accounts:novo_diretoria_login')
        current = data.get('current') or {}
        step_data = current.get('compromisso') or {}
        return render(request, self.template_name, {'step_data': step_data})

    def post(self, request):
        data = self._require_login_step(request)
        if data is None:
            return redirect('accounts:novo_diretoria_login')
        fields = _extract_fields(request.POST, self.field_names)
        fields['cpf'] = _normalize_cpf(fields.get('cpf'))
        fields['rg'] = _normalize_doc_text(fields.get('rg'))
        fields['declaracao_medica'] = _normalize_bool(fields.get('declaracao_medica'))

        required = [
            'nome', 'igreja', 'endereco', 'distrito', 'numero', 'bairro', 'cep', 'cidade',
            'estado', 'email', 'whatsapp', 'telefone_residencial', 'telefone_comercial',
            'nascimento', 'estado_civil', 'cpf', 'rg',
            'possui_limitacao_saude', 'escolaridade', 'foto_3x4', 'assinatura_compromisso',
        ]
        missing = [name for name in required if not str(fields.get(name, '')).strip()]
        if not fields.get('declaracao_medica'):
            missing.append('declaracao_medica')
        if missing:
            messages.error(request, 'Preencha todos os campos obrigatórios do compromisso.')
            return render(request, self.template_name, {'step_data': fields})

        cpf_duplicate = _find_duplicate_document('cpf_aventureiro', fields.get('cpf'))
        if cpf_duplicate:
            messages.error(request, cpf_duplicate)
            return render(request, self.template_name, {'step_data': fields})
        rg_duplicate = _find_duplicate_document('rg', fields.get('rg'))
        if rg_duplicate:
            messages.error(request, rg_duplicate)
            return render(request, self.template_name, {'step_data': fields})

        current = data.get('current') or {}
        current['compromisso'] = fields
        data['current'] = current
        _set_new_diretoria_flow_data(request.session, data)
        return redirect('accounts:novo_diretoria_termo')


class NovoCadastroDiretoriaTermoView(View):
    template_name = 'novo_diretoria/termo_imagem.html'
    field_names = [
        'nome_diretoria_termo', 'nacionalidade_diretoria_termo', 'responsavel_nome_termo',
        'responsavel_nacionalidade_termo', 'responsavel_estado_civil_termo',
        'responsavel_rg_termo', 'responsavel_cpf_termo', 'responsavel_endereco_termo',
        'responsavel_numero_termo', 'responsavel_cidade_termo', 'responsavel_estado_termo',
        'cidade_data', 'dia_data', 'mes_data', 'ano_data', 'telefone_contato_termo',
        'email_contato_termo', 'assinatura_termo_imagem', 'autorizacao_imagem',
    ]

    def _require_compromisso_step(self, request):
        data = _new_diretoria_flow_data(request.session)
        current = data.get('current') or {}
        if not data.get('login') or not current.get('compromisso'):
            return None
        return data

    def get(self, request):
        data = self._require_compromisso_step(request)
        if data is None:
            messages.error(request, 'Preencha o compromisso da diretoria antes do termo.')
            return redirect('accounts:novo_diretoria_compromisso')
        compromisso = data.get('current', {}).get('compromisso', {})
        termo = data.get('current', {}).get('termo_imagem', {})
        initial = _date_parts_today()
        initial.update({
            'nome_diretoria_termo': compromisso.get('nome', ''),
            'nacionalidade_diretoria_termo': 'Brasileiro',
            'responsavel_nome_termo': compromisso.get('nome', ''),
            'responsavel_nacionalidade_termo': 'Brasileiro',
            'responsavel_estado_civil_termo': compromisso.get('estado_civil', ''),
            'responsavel_rg_termo': compromisso.get('rg', ''),
            'responsavel_cpf_termo': compromisso.get('cpf', ''),
            'responsavel_endereco_termo': compromisso.get('endereco', ''),
            'responsavel_numero_termo': compromisso.get('numero', ''),
            'responsavel_cidade_termo': compromisso.get('cidade', ''),
            'responsavel_estado_termo': compromisso.get('estado', ''),
            'telefone_contato_termo': compromisso.get('whatsapp', ''),
            'email_contato_termo': compromisso.get('email', ''),
            'cidade_data': compromisso.get('cidade', ''),
        })
        initial.update(termo)
        _apply_date_defaults(initial)
        return render(request, self.template_name, {'initial': initial, 'step_data': termo})

    def post(self, request):
        data = self._require_compromisso_step(request)
        if data is None:
            messages.error(request, 'Preencha o compromisso da diretoria antes do termo.')
            return redirect('accounts:novo_diretoria_compromisso')
        fields = _extract_fields(request.POST, self.field_names)
        fields['autorizacao_imagem'] = _normalize_bool(fields.get('autorizacao_imagem'))
        _apply_date_defaults(fields)
        if not str(fields.get('nacionalidade_diretoria_termo', '')).strip():
            fields['nacionalidade_diretoria_termo'] = 'Brasileiro'
        if not str(fields.get('responsavel_nacionalidade_termo', '')).strip():
            fields['responsavel_nacionalidade_termo'] = 'Brasileiro'

        required = [
            'nome_diretoria_termo', 'responsavel_nome_termo', 'responsavel_rg_termo',
            'responsavel_cpf_termo', 'responsavel_endereco_termo', 'responsavel_numero_termo',
            'responsavel_cidade_termo', 'responsavel_estado_termo',
            'cidade_data', 'dia_data', 'mes_data', 'ano_data',
            'telefone_contato_termo', 'email_contato_termo', 'assinatura_termo_imagem',
        ]
        missing = [name for name in required if not str(fields.get(name, '')).strip()]
        if not fields.get('autorizacao_imagem'):
            missing.append('autorizacao_imagem')
        if missing:
            messages.error(request, 'Preencha todos os campos obrigatórios do termo de imagem.')
            initial = _date_parts_today()
            initial.update(fields)
            return render(request, self.template_name, {'initial': initial, 'step_data': fields})

        current = data.get('current') or {}
        current['termo_imagem'] = fields
        data['current'] = current
        _set_new_diretoria_flow_data(request.session, data)
        return redirect('accounts:novo_diretoria_resumo')


class NovoCadastroDiretoriaResumoView(View):
    template_name = 'novo_diretoria/resumo.html'

    def _require_steps(self, request):
        data = _new_diretoria_flow_data(request.session)
        current = data.get('current') or {}
        if data.get('login') and current.get('compromisso') and current.get('termo_imagem'):
            return data
        return None

    def get(self, request):
        data = self._require_steps(request)
        if data is None:
            messages.error(request, 'Complete as etapas do cadastro da diretoria.')
            return redirect('accounts:novo_diretoria_login')
        compromisso = data['current']['compromisso']
        return render(request, self.template_name, {
            'login_username': data['login'].get('username', ''),
            'nome_diretoria': compromisso.get('nome', ''),
            'ok_items': [
                'Login criado',
                'Compromisso voluntariado preenchido',
                'Termo de imagem assinado',
            ],
        })

    def post(self, request):
        data = self._require_steps(request)
        if data is None:
            messages.error(request, 'Complete as etapas do cadastro da diretoria.')
            return redirect('accounts:novo_diretoria_login')

        login_data = data.get('login', {})
        compromisso = data.get('current', {}).get('compromisso', {})
        termo = data.get('current', {}).get('termo_imagem', {})
        username = str(login_data.get('username', '')).strip()
        password = login_data.get('password')

        if not username or not password:
            messages.error(request, 'Sessão de login inválida. Refaça o cadastro da diretoria.')
            return redirect('accounts:novo_diretoria_login')

        try:
            nascimento = date.fromisoformat(compromisso.get('nascimento', ''))
        except ValueError:
            messages.error(request, 'Data de nascimento inválida. Volte ao compromisso e corrija.')
            return redirect('accounts:novo_diretoria_compromisso')

        try:
            with transaction.atomic():
                user = User.objects.create_user(username=username, password=password)
                access, _ = UserAccess.objects.get_or_create(
                    user=user,
                    defaults={'role': UserAccess.ROLE_DIRETORIA, 'profiles': [UserAccess.ROLE_DIRETORIA]},
                )
                access.add_profile(UserAccess.ROLE_DIRETORIA)
                access.save(update_fields=['role', 'profiles', 'updated_at'])

                diretoria = Diretoria.objects.create(
                    user=user,
                    nome=compromisso.get('nome', ''),
                    igreja=compromisso.get('igreja', ''),
                    endereco=compromisso.get('endereco', ''),
                    distrito=compromisso.get('distrito', ''),
                    numero=compromisso.get('numero', ''),
                    bairro=compromisso.get('bairro', ''),
                    cep=compromisso.get('cep', ''),
                    cidade=compromisso.get('cidade', ''),
                    estado=compromisso.get('estado', ''),
                    email=compromisso.get('email', ''),
                    whatsapp=compromisso.get('whatsapp', ''),
                    telefone_residencial=compromisso.get('telefone_residencial', ''),
                    telefone_comercial=compromisso.get('telefone_comercial', ''),
                    nascimento=nascimento,
                    estado_civil=compromisso.get('estado_civil', ''),
                    cpf=compromisso.get('cpf', ''),
                    rg=compromisso.get('rg', ''),
                    conjuge=compromisso.get('conjuge', ''),
                    filho_1=compromisso.get('filho_1', ''),
                    filho_2=compromisso.get('filho_2', ''),
                    filho_3=compromisso.get('filho_3', ''),
                    possui_limitacao_saude=compromisso.get('possui_limitacao_saude', ''),
                    limitacao_saude_descricao=compromisso.get('limitacao_saude_descricao', ''),
                    escolaridade=compromisso.get('escolaridade', ''),
                    autorizacao_imagem=bool(termo.get('autorizacao_imagem')),
                    declaracao_medica=bool(compromisso.get('declaracao_medica')),
                )

                photo = decode_photo(compromisso.get('foto_3x4'))
                if photo:
                    diretoria.foto.save(photo.name, photo, save=False)
                assinatura_compromisso = decode_signature(compromisso.get('assinatura_compromisso'), 'diretoria_compromisso')
                if assinatura_compromisso:
                    diretoria.assinatura.save(assinatura_compromisso.name, assinatura_compromisso, save=False)
                diretoria.save()

                ficha = DiretoriaFicha.objects.create(
                    diretoria=diretoria,
                    compromisso_data=compromisso,
                    termo_imagem_data=termo,
                )
                assinatura_compromisso_ficha = decode_signature(compromisso.get('assinatura_compromisso'), 'diretoria_compromisso')
                if assinatura_compromisso_ficha:
                    ficha.assinatura_compromisso.save(
                        assinatura_compromisso_ficha.name,
                        assinatura_compromisso_ficha,
                        save=False,
                    )
                assinatura_termo = decode_signature(termo.get('assinatura_termo_imagem'), 'diretoria_termo_imagem')
                if assinatura_termo:
                    ficha.assinatura_termo_imagem.save(assinatura_termo.name, assinatura_termo, save=False)
                ficha.save()
        except IntegrityError:
            messages.error(request, 'Não foi possível finalizar: username já existe ou há conflito de dados. Tente outro username.')
            return redirect('accounts:novo_diretoria_login')
        except Exception:
            messages.error(request, 'Falha ao finalizar cadastro da diretoria. Revise os dados e tente novamente.')
            return redirect('accounts:novo_diretoria_resumo')

        _dispatch_cadastro_notifications('Diretoria', user, diretoria.nome)
        _clear_new_diretoria_flow(request.session)
        messages.success(request, 'Cadastro da diretoria concluído com sucesso. Faça login para continuar.')
        return redirect('accounts:login')


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
        if not _has_menu_permission(request.user, 'aventureiros'):
            messages.error(request, 'Seu perfil não possui permissão para acessar aventureiros gerais.')
            return redirect('accounts:painel')
        aventureiros = Aventureiro.objects.select_related('responsavel', 'responsavel__user').order_by('nome')
        context = {'aventureiros': aventureiros}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class AventureiroGeralDetalheView(LoginRequiredMixin, View):
    template_name = 'meus_dados_aventureiro.html'

    def get(self, request, pk):
        if not _has_menu_permission(request.user, 'aventureiros'):
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
        if not _has_menu_permission(request.user, 'usuarios'):
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


class PermissoesView(LoginRequiredMixin, View):
    template_name = 'permissoes.html'

    def _guard(self, request):
        if not _has_menu_permission(request.user, 'permissoes'):
            messages.error(request, 'Seu perfil não possui permissão para acessar permissões.')
            return redirect('accounts:painel')
        return None

    def _build_context(self, request):
        _ensure_default_access_groups()
        groups = list(AccessGroup.objects.prefetch_related('users').order_by('name'))
        group_map = {group.code: group for group in groups}
        groups_by_id = {group.pk: set(_normalize_menu_keys(group.menu_permissions)) for group in groups}
        accesses = list(
            UserAccess.objects
            .select_related('user', 'user__responsavel', 'user__diretoria')
            .order_by('user__username')
        )
        rows = []
        for access in accesses:
            if not access.user.access_groups.exists():
                default_codes = _default_group_codes_for_access(access)
                default_ids = [group_map[code].pk for code in default_codes if code in group_map]
                if default_ids:
                    access.user.access_groups.set(default_ids)
            display = _user_display_data(access.user)
            user_group_ids = set(access.user.access_groups.values_list('id', flat=True))
            group_permissions = set()
            for group_id in user_group_ids:
                group_permissions.update(groups_by_id.get(group_id, set()))
            menu_allow = set(_normalize_menu_keys(access.menu_allow))
            has_user_marks = bool(menu_allow)
            override_active = bool(menu_allow and (menu_allow != group_permissions))
            rows.append({
                'access': access,
                'user': access.user,
                'nome_completo': display['nome_completo'],
                'foto_url': display['foto_url'],
                'group_ids': user_group_ids,
                'menu_allow': menu_allow,
                'has_user_marks': has_user_marks,
                'override_active': override_active,
            })
        rows.sort(key=lambda row: (_profile_order_weight(row['access']), row['user'].username.lower()))

        context = {
            'groups': groups,
            'users': rows,
            'menu_items': MENU_ITEMS,
        }
        context.update(_sidebar_context(request))
        return context

    def get(self, request):
        guard = self._guard(request)
        if guard:
            return guard
        return render(request, self.template_name, self._build_context(request))

    def post(self, request):
        guard = self._guard(request)
        if guard:
            return guard

        _ensure_default_access_groups()
        action = request.POST.get('action', '').strip()

        if action == 'create_group':
            code = str(request.POST.get('group_code', '')).strip().lower()
            name = str(request.POST.get('group_name', '')).strip()
            if not code or not name:
                messages.error(request, 'Informe código e nome do grupo.')
            elif AccessGroup.objects.filter(code=code).exists():
                messages.error(request, 'Já existe um grupo com esse código.')
            else:
                AccessGroup.objects.create(code=code, name=name, menu_permissions=['inicio', 'meus_dados'])
                messages.success(request, f'Grupo "{name}" criado com sucesso.')

        elif action == 'save_group_menus':
            groups = AccessGroup.objects.all()
            for group in groups:
                selected = []
                for key, _label in MENU_ITEMS:
                    if request.POST.get(f'g{group.pk}_menu_{key}'):
                        selected.append(key)
                group.menu_permissions = _normalize_menu_keys(selected)
                group.save(update_fields=['menu_permissions', 'updated_at'])
            messages.success(request, 'Permissões de menu dos grupos atualizadas.')

        elif action == 'save_memberships':
            groups = list(AccessGroup.objects.all())
            users = list(User.objects.all())
            for user in users:
                selected_group_ids = []
                for group in groups:
                    if request.POST.get(f'ug{user.pk}_{group.pk}'):
                        selected_group_ids.append(group.pk)
                user.access_groups.set(selected_group_ids)
            messages.success(request, 'Vínculo de usuários e grupos atualizado.')

        elif action == 'save_user_overrides':
            accesses = UserAccess.objects.select_related('user').all()
            for access in accesses:
                allow = []
                for key, _label in MENU_ITEMS:
                    if request.POST.get(f'ux{access.user.pk}_{key}'):
                        allow.append(key)
                access.menu_allow = _normalize_menu_keys(allow)
                access.menu_deny = []
                access.save(update_fields=['menu_allow', 'menu_deny', 'updated_at'])
            messages.success(request, 'Permissões por usuário atualizadas.')

        elif action == 'delete_group':
            group_id = request.POST.get('group_id')
            group = AccessGroup.objects.filter(pk=group_id).first()
            if not group:
                messages.error(request, 'Grupo não encontrado.')
            elif group.code in {'diretor', 'responsavel', 'professor'}:
                messages.error(request, 'Não é possível excluir grupos padrão.')
            else:
                group.delete()
                messages.success(request, 'Grupo removido com sucesso.')

        return render(request, self.template_name, self._build_context(request))


def _documento_tipo_label(doc_type):
    mapping = dict(DocumentoInscricaoGerado.TYPE_CHOICES)
    return mapping.get(doc_type, doc_type)


def _build_documento_gerado_context(documento):
    aventureiro = documento.aventureiro
    responsavel = aventureiro.responsavel
    ficha = getattr(aventureiro, 'ficha_completa', None)
    inscricao = (ficha.inscricao_data if ficha else {}) or {}
    medica = (ficha.ficha_medica_data if ficha else {}) or {}
    declaracao = (ficha.declaracao_medica_data if ficha else {}) or {}
    termo = (ficha.termo_imagem_data if ficha else {}) or {}

    return {
        'documento': documento,
        'doc_label': _documento_tipo_label(documento.doc_type),
        'aventureiro': aventureiro,
        'responsavel': responsavel,
        'ficha': ficha,
        'inscricao': inscricao,
        'medica': medica,
        'declaracao': declaracao,
        'termo': termo,
        'foto_url': aventureiro.foto.url if aventureiro.foto else '',
        'assinatura_inscricao_url': ficha.assinatura_inscricao.url if ficha and ficha.assinatura_inscricao else '',
        'assinatura_declaracao_url': ficha.assinatura_declaracao_medica.url if ficha and ficha.assinatura_declaracao_medica else '',
        'assinatura_termo_url': ficha.assinatura_termo_imagem.url if ficha and ficha.assinatura_termo_imagem else '',
    }




class DocumentosInscricaoView(LoginRequiredMixin, View):
    template_name = 'documentos_inscricao.html'

    def _guard(self, request):
        if not _has_menu_permission(request.user, 'documentos_inscricao'):
            messages.error(request, 'Seu perfil nao possui permissao para acessar documentos.')
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
        documentos_gerados = DocumentoInscricaoGerado.objects.select_related('aventureiro', 'aventureiro__responsavel', 'aventureiro__responsavel__user')
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
            'doc_generate_types': DocumentoInscricaoGerado.TYPE_CHOICES,
            'documentos_gerados': documentos_gerados,
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
        elif action == 'generate_doc':
            aventura_id = request.POST.get('aventureiro_id')
            doc_type = request.POST.get('doc_type')
            selected_template_id = request.POST.get('selected_template_id')
            aventureiro = Aventureiro.objects.filter(pk=aventura_id).first()
            if not aventureiro:
                messages.error(request, 'Selecione um aventureiro válido para gerar o documento.')
                return redirect(request.path)
            if doc_type not in {item[0] for item in DocumentoInscricaoGerado.TYPE_CHOICES}:
                messages.error(request, 'Selecione um tipo de documento válido.')
                return redirect(request.path)
            ficha = getattr(aventureiro, 'ficha_completa', None)
            if not ficha:
                messages.error(request, 'Esse aventureiro ainda não possui as fichas completas salvas.')
                return redirect(request.path)
            documento = DocumentoInscricaoGerado.objects.create(
                aventureiro=aventureiro,
                doc_type=doc_type,
                created_by=request.user,
            )
            messages.success(request, f'Documento gerado: {_documento_tipo_label(doc_type)} para {aventureiro.nome}.')
            if selected_template_id and str(selected_template_id).isdigit():
                return redirect(f'{request.path}?template={selected_template_id}')
            return redirect(request.path)
        elif action == 'delete_generated_doc':
            doc_id = request.POST.get('doc_id')
            documento = DocumentoInscricaoGerado.objects.filter(pk=doc_id).first()
            if not documento:
                messages.error(request, 'Documento gerado não encontrado.')
                return redirect(request.path)
            documento.delete()
            messages.success(request, 'Documento gerado excluído com sucesso.')
            return redirect(request.path)
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


class DocumentoInscricaoVisualizarView(LoginRequiredMixin, View):
    template_name = 'documento_inscricao_visualizar.html'

    def get(self, request, pk):
        if not _has_menu_permission(request.user, 'documentos_inscricao'):
            messages.error(request, 'Seu perfil não possui permissão para visualizar documentos gerados.')
            return redirect('accounts:painel')
        documento = get_object_or_404(
            DocumentoInscricaoGerado.objects.select_related('aventureiro', 'aventureiro__responsavel', 'aventureiro__responsavel__user'),
            pk=pk,
        )
        context = _build_documento_gerado_context(documento)
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class DocumentoGerarView(LoginRequiredMixin, View):
    def get(self, request, template_id, kind, pk):
        if not _has_menu_permission(request.user, 'documentos_inscricao'):
            messages.error(request, 'Seu perfil nao possui permissao para gerar documentos.')
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
        if not _has_menu_permission(request.user, 'whatsapp'):
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
        diretoria_template = get_template_message(WhatsAppTemplate.TYPE_DIRETORIA)
        teste_template = get_template_message(WhatsAppTemplate.TYPE_TESTE)
        context = {
            'rows': self._users_context(),
            'queue': queue_stats(),
            'cadastro_template': cadastro_template,
            'diretoria_template': diretoria_template,
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
        diretoria_enabled = []
        for row in rows:
            user = row['user']
            pref = row['pref']
            prefix = f'u{user.pk}'
            pref.phone_number = normalize_phone_number(request.POST.get(f'{prefix}_phone', '').strip())
            pref.notify_cadastro = bool(request.POST.get(f'{prefix}_cadastro'))
            pref.notify_diretoria = bool(request.POST.get(f'{prefix}_diretoria'))
            pref.notify_financeiro = False
            pref.notify_geral = False
            pref.save(
                update_fields=[
                    'phone_number',
                    'notify_cadastro',
                    'notify_diretoria',
                    'notify_financeiro',
                    'notify_geral',
                    'updated_at',
                ]
            )
            if pref.notify_cadastro:
                cadastro_enabled.append(user.username)
            if pref.notify_diretoria:
                diretoria_enabled.append(user.username)

        WhatsAppTemplate.objects.update_or_create(
            notification_type=WhatsAppTemplate.TYPE_CADASTRO,
            defaults={'message_text': request.POST.get('template_cadastro', '').strip()},
        )
        WhatsAppTemplate.objects.update_or_create(
            notification_type=WhatsAppTemplate.TYPE_DIRETORIA,
            defaults={'message_text': request.POST.get('template_diretoria', '').strip()},
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
                    'diretoria_template': get_template_message(WhatsAppTemplate.TYPE_DIRETORIA),
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
        if diretoria_enabled:
            preview = ', '.join(diretoria_enabled[:6])
            suffix = '...' if len(diretoria_enabled) > 6 else ''
            messages.info(
                request,
                f'Diretoria marcado para: {preview}{suffix}',
            )
        else:
            messages.info(request, 'Nenhum contato está marcado para receber notificação de Diretoria.')

        context = {
            'rows': self._users_context(),
            'queue': queue_stats(),
            'cadastro_template': get_template_message(WhatsAppTemplate.TYPE_CADASTRO),
            'diretoria_template': get_template_message(WhatsAppTemplate.TYPE_DIRETORIA),
            'teste_template': get_template_message(WhatsAppTemplate.TYPE_TESTE),
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class UsuarioDetalheView(LoginRequiredMixin, View):
    template_name = 'usuario_detalhe.html'

    def get(self, request, pk):
        if not _has_menu_permission(request.user, 'usuarios'):
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
        if not _has_menu_permission(request.user, 'usuarios'):
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
        if not _has_menu_permission(request.user, 'usuarios'):
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
