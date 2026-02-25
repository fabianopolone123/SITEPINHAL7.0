import copy
import json
import os
import re
import hashlib
import hmac
from random import randint
from decimal import Decimal, InvalidOperation
from urllib import request as urllib_request, error as urllib_error

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

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
    Evento,
    EventoPreset,
    EventoPresenca,
    AuditLog,
    MensalidadeAventureiro,
    PagamentoMensalidade,
    LojaProduto,
    LojaProdutoVariacao,
)
from .audit import record_audit
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
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import date, datetime, timedelta

User = get_user_model()

MENU_ITEMS = [
    ('inicio', 'InÃ­cio'),
    ('meus_dados', 'Meus dados'),
    ('aventureiros', 'Aventureiros'),
    ('eventos', 'Eventos'),
    ('presenca', 'PresenÃ§a'),
    ('auditoria', 'Auditoria'),
    ('usuarios', 'UsuÃ¡rios'),
    ('financeiro', 'Financeiro'),
    ('loja', 'Loja'),
    ('whatsapp', 'WhatsApp'),
    ('documentos_inscricao', 'Documentos inscriÃ§Ã£o'),
    ('permissoes', 'PermissÃµes'),
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


def _available_profiles(access):
    profiles = []
    if access.user_id:
        profiles.extend(
            access.user.access_groups.order_by('code').values_list('code', flat=True)
        )
        if hasattr(access.user, 'diretoria'):
            profiles.append(UserAccess.ROLE_DIRETORIA)
        if hasattr(access.user, 'responsavel'):
            profiles.append(UserAccess.ROLE_RESPONSAVEL)
    profiles.extend(list(access.profiles or []))
    if access.role:
        profiles.append(access.role)
    deduped = []
    seen = set()
    for item in profiles:
        value = str(item or '').strip().lower()
        if value and value not in seen:
            deduped.append(value)
            seen.add(value)
    order = {
        UserAccess.ROLE_DIRETOR: 0,
        UserAccess.ROLE_DIRETORIA: 1,
        UserAccess.ROLE_RESPONSAVEL: 2,
        UserAccess.ROLE_PROFESSOR: 3,
    }
    deduped.sort(key=lambda item: (order.get(item, 99), item))
    return deduped


def _sync_access_profiles_from_groups(user, access=None):
    access = access or _ensure_user_access(user)
    profiles = []
    group_codes = user.access_groups.order_by('code').values_list('code', flat=True)
    profiles.extend(str(code or '').strip().lower() for code in group_codes)
    if hasattr(user, 'diretoria'):
        profiles.append(UserAccess.ROLE_DIRETORIA)
    if hasattr(user, 'responsavel'):
        profiles.append(UserAccess.ROLE_RESPONSAVEL)
    if access.role and not profiles:
        profiles.append(access.role)
    deduped = []
    seen = set()
    for item in profiles:
        value = str(item or '').strip().lower()
        if value and value not in seen:
            deduped.append(value)
            seen.add(value)
    new_role = _primary_role_from_profiles(deduped)
    if access.profiles != deduped or access.role != new_role:
        access.profiles = deduped
        access.role = new_role
        access.save(update_fields=['role', 'profiles', 'updated_at'])
    return access


def _profile_display_name(profile):
    return dict(UserAccess.ROLE_CHOICES).get(profile, profile or '')


def _group_codes_for_profile(profile):
    if profile == UserAccess.ROLE_DIRETOR:
        return {'diretor'}
    if profile == UserAccess.ROLE_DIRETORIA:
        return {'diretoria'}
    if profile == UserAccess.ROLE_RESPONSAVEL:
        return {'responsavel'}
    if profile == UserAccess.ROLE_PROFESSOR:
        return {'professor'}
    if profile:
        return {profile}
    return set()


def _get_active_profile(request, access=None):
    access = access or _ensure_user_access(request.user)
    profiles = _available_profiles(access)
    if not profiles:
        request.session.pop('active_profile', None)
        return ''
    selected = str(request.session.get('active_profile') or '').strip()
    if selected in profiles:
        return selected
    selected = profiles[0]
    request.session['active_profile'] = selected
    return selected


def _effective_menu_permissions(user, active_profile=''):
    access = _ensure_user_access(user)
    user_override = _normalize_menu_keys(access.menu_allow)
    if user_override:
        return user_override

    allowed = {'inicio', 'meus_dados'}
    profiles = set(_available_profiles(access))
    if active_profile and active_profile in profiles:
        profiles = {active_profile}
    if UserAccess.ROLE_DIRETOR in profiles or UserAccess.ROLE_DIRETORIA in profiles:
        allowed.update({'aventureiros', 'eventos', 'presenca', 'auditoria', 'usuarios', 'loja', 'whatsapp', 'documentos_inscricao', 'permissoes'})
    if UserAccess.ROLE_RESPONSAVEL in profiles:
        allowed.add('financeiro')
    allowed_group_codes = _group_codes_for_profile(active_profile) if active_profile else set()
    for group in user.access_groups.all():
        if active_profile and group.code not in allowed_group_codes:
            continue
        allowed.update(_normalize_menu_keys(group.menu_permissions))
    return sorted(allowed)


def _has_menu_permission(user_or_request, menu_key):
    if hasattr(user_or_request, 'user'):
        request = user_or_request
        active_profile = _get_active_profile(request)
        return menu_key in _effective_menu_permissions(request.user, active_profile=active_profile)
    return menu_key in _effective_menu_permissions(user_or_request)


def _sidebar_context(request):
    access = _ensure_user_access(request.user)
    active_profile = _get_active_profile(request, access=access)
    profile_options = [
        {'value': profile, 'label': _profile_display_name(profile)}
        for profile in _available_profiles(access)
    ]
    return {
        'is_diretor': access.has_profile(UserAccess.ROLE_DIRETOR),
        'active_profile': active_profile,
        'active_profile_label': _profile_display_name(active_profile),
        'profile_options': profile_options,
        'profile_switch_enabled': len(profile_options) > 1,
        'current_path': request.get_full_path(),
        'current_profiles': [_profile_display_name(item) for item in _available_profiles(access)],
        'menu_permissions': _effective_menu_permissions(request.user, active_profile=active_profile),
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
    if not _has_menu_permission(request, menu_key):
        messages.error(request, message)
        return redirect('accounts:painel')
    return None


def _generate_financeiro_entries_for_aventureiro(aventureiro, created_by=None, valor=None, reference_date=None):
    base_value = (valor if isinstance(valor, Decimal) else Decimal(valor or '35.00')).quantize(Decimal('0.01'))
    ref_date = reference_date or timezone.localdate()
    created_count = 0
    created_inscricao = 0
    created_mensalidades = 0

    for mes in range(ref_date.month, 13):
        tipo = (
            MensalidadeAventureiro.TIPO_INSCRICAO
            if mes == ref_date.month
            else MensalidadeAventureiro.TIPO_MENSALIDADE
        )
        item, created = MensalidadeAventureiro.objects.get_or_create(
            aventureiro=aventureiro,
            ano_referencia=ref_date.year,
            mes_referencia=mes,
            defaults={
                'created_by': created_by,
                'valor': base_value,
                'status': MensalidadeAventureiro.STATUS_PENDENTE,
                'tipo': tipo,
            },
        )
        if not created and item.tipo != tipo:
            item.tipo = tipo
            item.save(update_fields=['tipo', 'updated_at'])
        if created:
            created_count += 1
            if tipo == MensalidadeAventureiro.TIPO_INSCRICAO:
                created_inscricao += 1
            else:
                created_mensalidades += 1

    return {
        'created_count': created_count,
        'created_inscricao': created_inscricao,
        'created_mensalidades': created_mensalidades,
        'valor': base_value,
        'ano': ref_date.year,
        'mes_inicial': ref_date.month,
    }


class AlterarPerfilAtivoView(LoginRequiredMixin, View):
    def post(self, request):
        access = _ensure_user_access(request.user)
        available = set(_available_profiles(access))
        selected = str(request.POST.get('active_profile') or '').strip()
        if selected in available:
            request.session['active_profile'] = selected
        next_url = str(request.POST.get('next_url') or '').strip()
        if next_url.startswith('/'):
            return redirect(next_url)
        return redirect('accounts:painel')


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
        ('diretor', 'Diretor', ['inicio', 'meus_dados', 'aventureiros', 'eventos', 'presenca', 'auditoria', 'usuarios', 'financeiro', 'loja', 'whatsapp', 'documentos_inscricao', 'permissoes']),
        ('diretoria', 'Diretoria', ['inicio', 'meus_dados', 'aventureiros', 'eventos', 'presenca', 'auditoria', 'usuarios', 'whatsapp', 'documentos_inscricao', 'permissoes']),
        ('responsavel', 'Responsavel', ['inicio', 'meus_dados', 'financeiro']),
        ('professor', 'Professor', ['inicio', 'meus_dados']),
    ]
    for code, name, menus in defaults:
        group, _ = AccessGroup.objects.get_or_create(
            code=code,
            defaults={'name': name, 'menu_permissions': menus},
        )
        if group.name != name:
            group.name = name
            group.save(update_fields=['name', 'updated_at'])
        if code == 'responsavel':
            current_menus = _normalize_menu_keys(group.menu_permissions)
            if 'financeiro' not in current_menus:
                group.menu_permissions = list(current_menus) + ['financeiro']
                group.save(update_fields=['menu_permissions', 'updated_at'])


def _default_group_codes_for_access(access):
    profiles = set(access.profiles or [])
    if access.role:
        profiles.add(access.role)
    codes = set()
    if UserAccess.ROLE_DIRETOR in profiles:
        codes.add('diretor')
    if UserAccess.ROLE_DIRETORIA in profiles:
        codes.add('diretoria')
    if UserAccess.ROLE_RESPONSAVEL in profiles:
        codes.add('responsavel')
    if UserAccess.ROLE_PROFESSOR in profiles:
        codes.add('professor')
    return codes


def _primary_role_from_profiles(profiles):
    current = set(profiles or [])
    if UserAccess.ROLE_DIRETOR in current:
        return UserAccess.ROLE_DIRETOR
    if UserAccess.ROLE_DIRETORIA in current:
        return UserAccess.ROLE_DIRETORIA
    if UserAccess.ROLE_RESPONSAVEL in current:
        return UserAccess.ROLE_RESPONSAVEL
    if UserAccess.ROLE_PROFESSOR in current:
        return UserAccess.ROLE_PROFESSOR
    return UserAccess.ROLE_RESPONSAVEL




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


def _dispatch_signup_confirmation(user, tipo_cadastro, nome):
    if not user:
        return
    pref, _ = WhatsAppPreference.objects.get_or_create(user=user)
    phone_number = normalize_phone_number(pref.phone_number or resolve_user_phone(user))
    if not phone_number:
        return

    login_url = os.environ.get('PINHAL_LOGIN_URL', 'https://pinhaljunior.com.br/').strip() or 'https://pinhaljunior.com.br/'
    payload = {
        'tipo_cadastro': tipo_cadastro,
        'username': user.username,
        'nome': nome or user.username,
        'login_url': login_url,
        'data_hora': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M'),
    }
    template_text = get_template_message(WhatsAppTemplate.TYPE_CONFIRMACAO)
    text = render_message(template_text, payload)
    queue_item = WhatsAppQueue.objects.create(
        user=user,
        phone_number=phone_number,
        notification_type=WhatsAppQueue.TYPE_CONFIRMACAO,
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
PASSWORD_RECOVERY_SESSION_KEY = 'password_recovery'


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


def _password_recovery_data(session):
    return session.get(PASSWORD_RECOVERY_SESSION_KEY, {})


def _set_password_recovery_data(session, data):
    session[PASSWORD_RECOVERY_SESSION_KEY] = data
    session.modified = True


def _clear_password_recovery(session):
    if PASSWORD_RECOVERY_SESSION_KEY in session:
        del session[PASSWORD_RECOVERY_SESSION_KEY]
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


def _find_duplicate_document(field_name, normalized_value, scope='global'):
    value = str(normalized_value or '').strip()
    if not value:
        return None

    if field_name in {'cpf_aventureiro', 'cpf_pai', 'cpf_mae', 'cpf_responsavel', 'cpf_diretoria'}:
        if scope == 'inscricao':
            if field_name == 'cpf_aventureiro' and Aventureiro.objects.filter(cpf=value).exists():
                return 'CPF jÃ¡ cadastrado em aventureiro.'
            if field_name in {'cpf_pai', 'cpf_mae', 'cpf_responsavel'}:
                if Responsavel.objects.filter(pai_cpf=value).exists():
                    return 'CPF jÃ¡ cadastrado como CPF do pai.'
                if Responsavel.objects.filter(mae_cpf=value).exists():
                    return 'CPF jÃ¡ cadastrado como CPF da mÃ£e.'
                if Responsavel.objects.filter(responsavel_cpf=value).exists():
                    return 'CPF jÃ¡ cadastrado como CPF do responsÃ¡vel.'
            return None
        if scope == 'diretoria' or field_name == 'cpf_diretoria':
            if Diretoria.objects.filter(cpf=value).exists():
                return 'CPF jÃ¡ cadastrado em diretoria.'
            return None

        if Aventureiro.objects.filter(cpf=value).exists():
            return 'CPF jÃ¡ cadastrado em aventureiro.'
        if Diretoria.objects.filter(cpf=value).exists():
            return 'CPF jÃ¡ cadastrado em diretoria.'
        if Responsavel.objects.filter(pai_cpf=value).exists():
            return 'CPF jÃ¡ cadastrado como CPF do pai.'
        if Responsavel.objects.filter(mae_cpf=value).exists():
            return 'CPF jÃ¡ cadastrado como CPF da mÃ£e.'
        if Responsavel.objects.filter(responsavel_cpf=value).exists():
            return 'CPF jÃ¡ cadastrado como CPF do responsÃ¡vel.'
        return None

    if field_name == 'rg':
        if Aventureiro.objects.filter(rg=value).exists():
            return 'RG jÃ¡ cadastrado em aventureiro.'
        if Diretoria.objects.filter(rg=value).exists():
            return 'RG jÃ¡ cadastrado em diretoria.'
        return None

    if field_name == 'certidao_nascimento':
        if Aventureiro.objects.filter(certidao=value).exists():
            return 'CertidÃ£o jÃ¡ cadastrada em aventureiro.'
        return None

    return None


def _date_parts_today():
    now = timezone.localtime(timezone.now())
    meses_ptbr = [
        'Janeiro',
        'Fevereiro',
        'MarÃ§o',
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
        'march': 'MarÃ§o',
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
        'marco': 'MarÃ§o',
        'marÃ§o': 'MarÃ§o',
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
        'pai_ausente',
        'nome_pai',
        'email_pai',
        'cpf_pai',
        'tel_pai',
        'cel_pai',
        'mae_ausente',
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


def _inscricao_parent_fields_from_responsavel(responsavel):
    if not responsavel:
        return {}
    return {
        'pai_ausente': '',
        'nome_pai': responsavel.pai_nome or '',
        'email_pai': responsavel.pai_email or '',
        'cpf_pai': responsavel.pai_cpf or '',
        'tel_pai': responsavel.pai_telefone or '',
        'cel_pai': responsavel.pai_celular or '',
        'mae_ausente': '',
        'nome_mae': responsavel.mae_nome or '',
        'email_mae': responsavel.mae_email or '',
        'cpf_mae': responsavel.mae_cpf or '',
        'tel_mae': responsavel.mae_telefone or '',
        'cel_mae': responsavel.mae_celular or '',
        'nome_responsavel': responsavel.responsavel_nome or '',
        'parentesco': responsavel.responsavel_parentesco or '',
        'cpf_responsavel': responsavel.responsavel_cpf or '',
        'email_responsavel': responsavel.responsavel_email or '',
        'tel_responsavel': responsavel.responsavel_telefone or '',
        'cel_responsavel': responsavel.responsavel_celular or '',
    }


class RegisterView(View):
    template_name = 'register.html'

    def get(self, request):
        return render(request, self.template_name)


class PasswordRecoveryView(View):
    template_name = 'password_recovery.html'
    code_ttl_minutes = 10
    max_attempts = 5

    def _mask_phone(self, phone):
        digits = ''.join(ch for ch in str(phone or '') if ch.isdigit())
        if len(digits) < 4:
            return '***'
        return f'***{digits[-4:]}'

    def _find_user_by_cpf(self, cpf_digits):
        if not cpf_digits:
            return None
        responsavel = Responsavel.objects.select_related('user').filter(responsavel_cpf=cpf_digits).first()
        if responsavel and responsavel.user:
            return responsavel.user
        for item in Responsavel.objects.select_related('user').exclude(responsavel_cpf=''):
            if _normalize_cpf(item.responsavel_cpf) == cpf_digits:
                return item.user
        diretoria = Diretoria.objects.select_related('user').filter(cpf=cpf_digits).first()
        if diretoria and diretoria.user:
            return diretoria.user
        for item in Diretoria.objects.select_related('user').exclude(cpf=''):
            if _normalize_cpf(item.cpf) == cpf_digits:
                return item.user
        return None

    def _context(self, recovery_data):
        stage = recovery_data.get('stage') or 'lookup'
        return {
            'stage': stage,
            'cpf': recovery_data.get('cpf', ''),
            'username': recovery_data.get('username', ''),
            'phone_masked': recovery_data.get('phone_masked', ''),
            'code_sent': bool(recovery_data.get('code_sent')),
        }

    def get(self, request):
        recovery_data = _password_recovery_data(request.session)
        if not recovery_data:
            recovery_data = {'stage': 'lookup'}
            _set_password_recovery_data(request.session, recovery_data)
        return render(request, self.template_name, self._context(recovery_data))

    def post(self, request):
        action = (request.POST.get('action') or '').strip()
        recovery_data = _password_recovery_data(request.session)
        if not recovery_data:
            recovery_data = {'stage': 'lookup'}

        if action == 'lookup_cpf':
            cpf_digits = _normalize_cpf(request.POST.get('cpf'))
            user = self._find_user_by_cpf(cpf_digits)
            if not user:
                messages.error(request, 'CPF nÃ£o encontrado.')
                recovery_data = {'stage': 'lookup', 'cpf': cpf_digits}
                _set_password_recovery_data(request.session, recovery_data)
                return render(request, self.template_name, self._context(recovery_data))
            phone_number = normalize_phone_number(resolve_user_phone(user))
            if not phone_number:
                messages.error(request, 'NÃ£o foi encontrado WhatsApp vÃ¡lido para este cadastro.')
                recovery_data = {'stage': 'lookup', 'cpf': cpf_digits}
                _set_password_recovery_data(request.session, recovery_data)
                return render(request, self.template_name, self._context(recovery_data))

            recovery_data = {
                'stage': 'confirm_send',
                'cpf': cpf_digits,
                'user_id': user.id,
                'username': user.username,
                'phone': phone_number,
                'phone_masked': self._mask_phone(phone_number),
                'attempts': 0,
                'verified': False,
            }
            _set_password_recovery_data(request.session, recovery_data)
            return render(request, self.template_name, self._context(recovery_data))

        if action == 'send_code':
            user_id = recovery_data.get('user_id')
            phone_number = recovery_data.get('phone')
            if not user_id or not phone_number:
                messages.error(request, 'Fluxo de recuperaÃ§Ã£o invÃ¡lido. Informe o CPF novamente.')
                _clear_password_recovery(request.session)
                return redirect('accounts:password_recovery')
            user = User.objects.filter(pk=user_id).first()
            if not user:
                messages.error(request, 'UsuÃ¡rio nÃ£o encontrado. Informe o CPF novamente.')
                _clear_password_recovery(request.session)
                return redirect('accounts:password_recovery')

            code = str(randint(1000, 9999))
            message_text = (
                'Pinhal Junior - Recuperacao de senha\n'
                f'Usuario: {user.username}\n'
                f'Codigo: {code}\n'
                f'Valido por {self.code_ttl_minutes} minutos.'
            )
            success, _provider_id, error_message = send_wapi_text(phone_number, message_text)
            if not success:
                messages.error(request, f'Falha ao enviar cÃ³digo por WhatsApp: {error_message}')
                recovery_data['stage'] = 'confirm_send'
                _set_password_recovery_data(request.session, recovery_data)
                return render(request, self.template_name, self._context(recovery_data))

            expires_at = timezone.localtime(timezone.now() + timedelta(minutes=self.code_ttl_minutes)).isoformat()
            recovery_data.update({
                'stage': 'verify_code',
                'code': code,
                'expires_at': expires_at,
                'code_sent': True,
                'attempts': 0,
                'verified': False,
            })
            _set_password_recovery_data(request.session, recovery_data)
            messages.success(request, 'CÃ³digo enviado no WhatsApp cadastrado.')
            return render(request, self.template_name, self._context(recovery_data))

        if action == 'verify_code':
            typed_code = ''.join(ch for ch in str(request.POST.get('code') or '') if ch.isdigit())[:4]
            expected_code = str(recovery_data.get('code') or '')
            expires_at_raw = str(recovery_data.get('expires_at') or '')
            if not expected_code or not expires_at_raw:
                messages.error(request, 'CÃ³digo nÃ£o gerado. Solicite um novo envio.')
                recovery_data['stage'] = 'confirm_send'
                _set_password_recovery_data(request.session, recovery_data)
                return render(request, self.template_name, self._context(recovery_data))
            try:
                expires_at = datetime.fromisoformat(expires_at_raw)
            except ValueError:
                expires_at = timezone.localtime(timezone.now()) - timedelta(seconds=1)
            now = timezone.localtime(timezone.now())
            if now > expires_at:
                messages.error(request, 'CÃ³digo expirado. Clique em recuperar para gerar novo cÃ³digo.')
                recovery_data['stage'] = 'confirm_send'
                recovery_data['code_sent'] = False
                recovery_data['verified'] = False
                recovery_data.pop('code', None)
                recovery_data.pop('expires_at', None)
                _set_password_recovery_data(request.session, recovery_data)
                return render(request, self.template_name, self._context(recovery_data))
            if typed_code != expected_code:
                attempts = int(recovery_data.get('attempts') or 0) + 1
                recovery_data['attempts'] = attempts
                if attempts >= self.max_attempts:
                    messages.error(request, 'Muitas tentativas invÃ¡lidas. Solicite um novo cÃ³digo.')
                    recovery_data['stage'] = 'confirm_send'
                    recovery_data['code_sent'] = False
                    recovery_data['verified'] = False
                    recovery_data.pop('code', None)
                    recovery_data.pop('expires_at', None)
                else:
                    messages.error(request, f'CÃ³digo invÃ¡lido. Tentativas restantes: {self.max_attempts - attempts}.')
                    recovery_data['stage'] = 'verify_code'
                _set_password_recovery_data(request.session, recovery_data)
                return render(request, self.template_name, self._context(recovery_data))

            recovery_data['stage'] = 'reset_password'
            recovery_data['verified'] = True
            _set_password_recovery_data(request.session, recovery_data)
            messages.success(request, 'CÃ³digo validado. Defina sua nova senha.')
            return render(request, self.template_name, self._context(recovery_data))

        if action == 'reset_password':
            if not recovery_data.get('verified'):
                messages.error(request, 'Valide o cÃ³digo antes de redefinir a senha.')
                recovery_data['stage'] = 'verify_code'
                _set_password_recovery_data(request.session, recovery_data)
                return render(request, self.template_name, self._context(recovery_data))
            password = str(request.POST.get('password') or '')
            password_confirm = str(request.POST.get('password_confirm') or '')
            if len(password) < 6:
                messages.error(request, 'A senha precisa ter pelo menos 6 caracteres.')
                recovery_data['stage'] = 'reset_password'
                _set_password_recovery_data(request.session, recovery_data)
                return render(request, self.template_name, self._context(recovery_data))
            if password != password_confirm:
                messages.error(request, 'As senhas nÃ£o conferem.')
                recovery_data['stage'] = 'reset_password'
                _set_password_recovery_data(request.session, recovery_data)
                return render(request, self.template_name, self._context(recovery_data))
            user = User.objects.filter(pk=recovery_data.get('user_id')).first()
            if not user:
                messages.error(request, 'UsuÃ¡rio nÃ£o encontrado.')
                _clear_password_recovery(request.session)
                return redirect('accounts:password_recovery')
            user.set_password(password)
            user.save(update_fields=['password'])
            _clear_password_recovery(request.session)
            messages.success(request, 'Senha redefinida com sucesso. FaÃ§a login com a nova senha.')
            return redirect('accounts:login')

        return render(request, self.template_name, self._context(recovery_data))


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
        'pai_ausente',
        'nome_mae', 'email_mae', 'cpf_mae', 'tel_mae', 'cel_mae', 'nome_responsavel',
        'mae_ausente',
        'parentesco', 'cpf_responsavel', 'email_responsavel', 'tel_responsavel',
        'cel_responsavel', 'assinatura_inscricao', 'foto_3x4',
        'cidade_data', 'dia_data', 'mes_data', 'ano_data',
    ]

    def _require_login_step(self, request):
        data = _new_flow_data(request.session)
        if not data.get('login'):
            messages.error(request, 'Comece pelo login do responsÃ¡vel.')
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
        if not step_data and data.get('existing_responsavel_id'):
            responsavel = (
                Responsavel.objects
                .filter(
                    pk=data.get('existing_responsavel_id'),
                    user_id=data.get('existing_user_id'),
                )
                .first()
            )
            step_data = _inscricao_parent_fields_from_responsavel(responsavel)
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
        pai_ausente = _normalize_bool(fields.get('pai_ausente'))
        mae_ausente = _normalize_bool(fields.get('mae_ausente'))
        fields['pai_ausente'] = 'on' if pai_ausente else ''
        fields['mae_ausente'] = 'on' if mae_ausente else ''
        if pai_ausente:
            for key in ('nome_pai', 'email_pai', 'cpf_pai', 'tel_pai', 'cel_pai'):
                fields[key] = ''
        if mae_ausente:
            for key in ('nome_mae', 'email_mae', 'cpf_mae', 'tel_mae', 'cel_mae'):
                fields[key] = ''
        is_existing_responsavel_flow = bool(data.get('existing_responsavel_id'))
        duplicate_fields = ['cpf_aventureiro', 'rg', 'certidao_nascimento']
        if not is_existing_responsavel_flow:
            if not pai_ausente:
                duplicate_fields.append('cpf_pai')
            if not mae_ausente:
                duplicate_fields.append('cpf_mae')
            duplicate_fields.append('cpf_responsavel')
        for field_name in duplicate_fields:
            duplicate_message = _find_duplicate_document(field_name, fields.get(field_name), scope='inscricao')
            if duplicate_message:
                messages.error(request, duplicate_message)
                initial = _date_parts_today()
                initial.update(fields)
                return render(request, self.template_name, {
                    'initial': initial,
                    'step_data': fields,
                    'has_saved_aventureiros': bool(data.get('aventures')),
                })
        required = [
            'nome_completo', 'sexo', 'data_nascimento', 'colegio', 'serie', 'bolsa_familia',
            'endereco', 'bairro', 'cidade', 'cep', 'estado',
            'certidao_nascimento', 'religiao', 'rg',
            'orgao_expedidor', 'cpf_aventureiro', 'tem_whatsapp', 'tamanho_camiseta',
            'nome_responsavel', 'parentesco', 'cpf_responsavel', 'email_responsavel', 'cel_responsavel',
            'assinatura_inscricao', 'foto_3x4',
        ]
        missing = [name for name in required if not str(fields.get(name, '')).strip()]
        if missing:
            messages.error(request, 'Preencha os campos obrigatÃ³rios e assine a ficha de inscriÃ§Ã£o.')
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
            return JsonResponse({'ok': False, 'error': 'Campo invÃ¡lido.'}, status=400)

        data = _new_flow_data(request.session)
        is_existing_responsavel_flow = bool(data.get('existing_responsavel_id'))

        if field in {'cpf_aventureiro', 'cpf_pai', 'cpf_mae', 'cpf_responsavel'}:
            normalized = _normalize_cpf(value)
        elif field in {'rg', 'certidao_nascimento'}:
            normalized = _normalize_doc_text(value)
        else:
            return JsonResponse({'ok': False, 'error': 'Campo nÃ£o suportado.'}, status=400)

        duplicate_message = ''
        if not (
            is_existing_responsavel_flow
            and field in {'cpf_pai', 'cpf_mae', 'cpf_responsavel'}
        ):
            duplicate_message = _find_duplicate_document(field, normalized, scope='inscricao')
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
            messages.error(request, 'Complete a ficha de inscriÃ§Ã£o antes.')
            return redirect('accounts:novo_cadastro_inscricao')
        current = data.get('current') or {}
        step_data = current.get('medica') or {}
        return render(request, self.template_name, {'step_data': step_data})

    def post(self, request):
        data = self._require_inscricao_step(request)
        if data is None:
            messages.error(request, 'Complete a ficha de inscriÃ§Ã£o antes.')
            return redirect('accounts:novo_cadastro_inscricao')
        fields = _extract_fields(request.POST, self.field_names)
        if not str(fields.get('plano_saude', '')).strip():
            messages.error(request, 'Informe se tem plano de saÃºde para continuar.')
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
            messages.error(request, 'Preencha todos os campos obrigatÃ³rios de condiÃ§Ãµes de saÃºde.')
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
            messages.error(request, 'Assine a declaraÃ§Ã£o mÃ©dica para continuar.')
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
            # Permite concluir os aventureiros jÃ¡ completos mesmo que a ficha atual esteja incompleta.
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
            messages.success(request, 'Aventureiro salvo temporariamente. Preencha o prÃ³ximo.')
            return redirect('accounts:novo_cadastro_inscricao')
        if action == 'finalizar':
            if self._is_current_complete(data):
                data['aventures'].append(data['current'])
            elif data.get('current'):
                messages.info(request, 'A ficha atual incompleta foi ignorada. Somente os aventureiros completos foram finalizados.')
            payload = data
            if not payload.get('aventures'):
                messages.error(request, 'Nenhum aventureiro completo para finalizar.')
                return redirect('accounts:novo_cadastro_inscricao')

            use_existing_user = bool(payload.get('existing_user_id'))
            first = payload['aventures'][0]['inscricao']

            if use_existing_user:
                if not request.user.is_authenticated or request.user.id != payload.get('existing_user_id'):
                    messages.error(request, 'SessÃ£o invÃ¡lida para adicionar aventureiro. FaÃ§a login novamente.')
                    return redirect('accounts:login')
                user = request.user
                responsavel = getattr(user, 'responsavel', None)
                if not responsavel:
                    messages.error(request, 'Conta sem perfil de responsÃ¡vel para adicionar aventureiro.')
                    return redirect('accounts:meus_dados')
                responsavel.pai_nome = first.get('nome_pai', '')
                responsavel.pai_cpf = first.get('cpf_pai', '')
                responsavel.pai_email = first.get('email_pai', '')
                responsavel.pai_telefone = first.get('tel_pai', '')
                responsavel.pai_celular = first.get('cel_pai', '')
                responsavel.mae_nome = first.get('nome_mae', '')
                responsavel.mae_cpf = first.get('cpf_mae', '')
                responsavel.mae_email = first.get('email_mae', '')
                responsavel.mae_telefone = first.get('tel_mae', '')
                responsavel.mae_celular = first.get('cel_mae', '')
                responsavel.responsavel_nome = first.get('nome_responsavel', '')
                responsavel.responsavel_parentesco = first.get('parentesco', '')
                responsavel.responsavel_cpf = first.get('cpf_responsavel', '')
                responsavel.responsavel_email = first.get('email_responsavel', '')
                responsavel.responsavel_telefone = first.get('tel_responsavel', '')
                responsavel.responsavel_celular = first.get('cel_responsavel', '')
                responsavel.endereco = first.get('endereco', '')
                responsavel.bairro = first.get('bairro', '')
                responsavel.cidade = first.get('cidade', '')
                responsavel.cep = first.get('cep', '')
                responsavel.estado = first.get('estado', '')
                responsavel.save()
            else:
                login_data = payload.get('login', {})
                if not login_data:
                    messages.error(request, 'SessÃ£o invÃ¡lida. Reinicie o cadastro.')
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
                _generate_financeiro_entries_for_aventureiro(
                    aventureiro,
                    created_by=user if getattr(user, 'is_authenticated', False) else None,
                    valor=Decimal('35.00'),
                )

            _dispatch_cadastro_notifications(
                'Cadastro completo',
                user,
                responsavel.responsavel_nome or responsavel.mae_nome or responsavel.pai_nome,
            )
            _dispatch_signup_confirmation(
                user,
                'Cadastro de responsÃ¡vel e aventureiro',
                responsavel.responsavel_nome or responsavel.mae_nome or responsavel.pai_nome,
            )
            _clear_new_flow(request.session)
            if use_existing_user:
                messages.success(request, 'Aventureiro adicionado com sucesso.')
                return redirect('accounts:meu_responsavel')
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
            'estado', 'email', 'whatsapp',
            'nascimento', 'estado_civil', 'cpf', 'rg',
            'possui_limitacao_saude', 'foto_3x4', 'assinatura_compromisso',
        ]
        missing = [name for name in required if not str(fields.get(name, '')).strip()]
        if not fields.get('declaracao_medica'):
            missing.append('declaracao_medica')
        if missing:
            messages.error(request, 'Preencha todos os campos obrigatÃ³rios do compromisso.')
            return render(request, self.template_name, {'step_data': fields})

        cpf_duplicate = _find_duplicate_document('cpf_diretoria', fields.get('cpf'), scope='diretoria')
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
            messages.error(request, 'Preencha todos os campos obrigatÃ³rios do termo de imagem.')
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
            messages.error(request, 'SessÃ£o de login invÃ¡lida. RefaÃ§a o cadastro da diretoria.')
            return redirect('accounts:novo_diretoria_login')

        try:
            nascimento = date.fromisoformat(compromisso.get('nascimento', ''))
        except ValueError:
            messages.error(request, 'Data de nascimento invÃ¡lida. Volte ao compromisso e corrija.')
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
            messages.error(request, 'NÃ£o foi possÃ­vel finalizar: username jÃ¡ existe ou hÃ¡ conflito de dados. Tente outro username.')
            return redirect('accounts:novo_diretoria_login')
        except Exception:
            messages.error(request, 'Falha ao finalizar cadastro da diretoria. Revise os dados e tente novamente.')
            return redirect('accounts:novo_diretoria_resumo')

        _dispatch_cadastro_notifications('Diretoria', user, diretoria.nome)
        _dispatch_signup_confirmation(user, 'Cadastro de diretoria', diretoria.nome)
        _clear_new_diretoria_flow(request.session)
        messages.success(request, 'Cadastro da diretoria concluÃ­do com sucesso. FaÃ§a login para continuar.')
        return redirect('accounts:login')


class LogoutRedirectView(View):
    def get(self, request):
        logout(request)
        messages.success(request, 'SessÃ£o encerrada. FaÃ§a login para continuar.')
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
            messages.success(request, 'ResponsÃ¡vel cadastrado com sucesso. Continue com a ficha do aventureiro.')
            return redirect('accounts:aventura')
        messages.error(request, 'HÃ¡ campos obrigatÃ³rios pendentes; corrija e envie novamente.')
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
            _dispatch_signup_confirmation(diretoria.user, 'Cadastro de diretoria', diretoria.nome)
            messages.success(request, 'Cadastro da diretoria concluÃ­do com sucesso. FaÃ§a login para continuar.')
            return redirect('accounts:login')
        messages.error(request, 'HÃ¡ campos obrigatÃ³rios pendentes; corrija e envie novamente.')
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
            messages.error(request, 'Complete primeiro os dados do responsÃ¡vel para continuar.')
            return redirect('accounts:responsavel')
        form = AventureiroForm()
        return render(request, self.template_name, self._build_context(form, request, responsavel))

    def post(self, request):
        responsavel = getattr(request.user, 'responsavel', None)
        if not responsavel:
            messages.error(request, 'Complete primeiro os dados do responsÃ¡vel para continuar.')
            return redirect('accounts:responsavel')
        form = AventureiroForm(request.POST)
        if form.is_valid():
            _enqueue_pending_aventure(request.session, form.cleaned_data)
            action = request.POST.get('action', 'save_confirm')
            messages.success(request, 'Ficha salva e encaminhada para revisÃ£o. VÃ¡ para a confirmaÃ§Ã£o para concluir o cadastro.')
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
            messages.error(request, 'Complete os dados do responsÃ¡vel antes de revisar os aventureiros.')
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
            messages.error(request, 'Complete os dados do responsÃ¡vel antes de revisar os aventureiros.')
            return redirect('accounts:responsavel')
        pending = _get_pending_aventures(request.session)
        if not pending:
            messages.error(request, 'NÃ£o hÃ¡ fichas pendentes para confirmar.')
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
        _dispatch_signup_confirmation(
            request.user,
            'Cadastro de responsÃ¡vel e aventureiro',
            responsavel.responsavel_nome or responsavel.mae_nome or responsavel.pai_nome,
        )
        _clear_pending_aventures(request.session)
        logout(request)
        messages.success(request, 'Cadastro finalizado com sucesso. FaÃ§a login novamente para continuar.')
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
        messages.error(request, 'Cadastre os dados do responsÃ¡vel antes de acessar esta Ã¡rea.')
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


class MeuResponsavelAdicionarAventureiroView(LoginRequiredMixin, View):
    def get(self, request):
        responsavel, redirect_response = _require_responsavel_or_redirect(request)
        if redirect_response:
            return redirect_response
        _clear_new_flow(request.session)
        data = _new_flow_data(request.session)
        data['login'] = {
            'username': request.user.username,
            # Existing responsible users reuse current account in finalization.
            'password': '',
        }
        data['existing_user_id'] = request.user.id
        data['existing_responsavel_id'] = responsavel.id
        _set_new_flow_data(request.session, data)
        messages.info(request, 'Preencha os dados do aventureiro para adicionar ao seu cadastro.')
        return redirect('accounts:novo_cadastro_inscricao')


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
            messages.success(request, 'Dados do responsÃ¡vel atualizados com sucesso.')
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
            'cardiaco': 'Problemas cardÃ­acos',
            'diabetico': 'Diabetes',
            'renal': 'Problemas renais',
            'psicologico': 'Problemas psicolÃ³gicos',
        }
        alergias_labels = {
            'alergia_pele': 'Alergia cutÃ¢nea (pele)',
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
        messages.error(request, 'Cadastre os dados da diretoria antes de acessar esta Ã¡rea.')
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
        form = DiretoriaDadosForm(request.POST, request.FILES, instance=diretoria)
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
        if not _has_menu_permission(request, 'aventureiros'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para acessar aventureiros gerais.')
            return redirect('accounts:painel')
        aventureiros = Aventureiro.objects.select_related('responsavel', 'responsavel__user').order_by('nome')
        context = {'aventureiros': aventureiros}
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class AventureiroGeralDetalheView(LoginRequiredMixin, View):
    template_name = 'meus_dados_aventureiro.html'

    def get(self, request, pk):
        if not _has_menu_permission(request, 'aventureiros'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para visualizar esse aventureiro.')
            return redirect('accounts:painel')
        aventureiro = get_object_or_404(Aventureiro, pk=pk)

        condicoes_labels = {
            'cardiaco': 'Problemas cardÃ­acos',
            'diabetico': 'Diabetes',
            'renal': 'Problemas renais',
            'psicologico': 'Problemas psicolÃ³gicos',
        }
        alergias_labels = {
            'alergia_pele': 'Alergia cutÃ¢nea (pele)',
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


class EventosView(LoginRequiredMixin, View):
    template_name = 'eventos.html'

    def _guard(self, request):
        if not _has_menu_permission(request, 'eventos'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para acessar eventos.')
            return redirect('accounts:painel')
        return None

    def _relative_event_time_label(self, event_date):
        if not event_date:
            return 'Sem data'
        today = timezone.localdate()
        delta = (event_date - today).days
        if delta == 0:
            return 'Hoje'
        if delta == 1:
            return 'AmanhÃ£'
        if delta == -1:
            return 'Ontem'
        if delta > 1:
            return f'Em {delta} dias'
        return f'HÃ¡ {abs(delta)} dias'

    def _context(self, request):
        eventos = list(Evento.objects.select_related('created_by').all())
        event_rows = []
        for evento in eventos:
            event_rows.append({
                'evento': evento,
                'relative_label': self._relative_event_time_label(evento.event_date),
            })
        presets = list(EventoPreset.objects.select_related('created_by').all())
        presets_json = [
            {
                'id': preset.id,
                'preset_name': preset.preset_name,
                'event_name': preset.event_name or '',
                'event_type': preset.event_type or '',
                'event_date': preset.event_date.isoformat() if preset.event_date else '',
                'event_time': preset.event_time.strftime('%H:%M') if preset.event_time else '',
                'fields_data': preset.fields_data or [],
            }
            for preset in presets
        ]
        context = {
            'eventos': event_rows,
            'presets': presets,
            'presets_json': presets_json,
        }
        context.update(_sidebar_context(request))
        return context

    def get(self, request):
        guard = self._guard(request)
        if guard:
            return guard
        return render(request, self.template_name, self._context(request))

    def post(self, request):
        guard = self._guard(request)
        if guard:
            return guard

        def _parse_event_schema():
            labels = request.POST.getlist('field_name[]') or request.POST.getlist('field_label[]')
            field_types = request.POST.getlist('field_type[]')
            values = request.POST.getlist('field_value[]')
            fields_data = []
            allowed_types = {'texto', 'data', 'hora', 'numero', 'booleano'}
            for index, label in enumerate(labels):
                current_label = (label or '').strip()
                current_type = (field_types[index] if index < len(field_types) else 'texto').strip().lower() or 'texto'
                current_value = (values[index] if index < len(values) else '').strip()
                if not (current_label or current_value):
                    continue
                if not current_label:
                    messages.error(request, 'Preencha o nome de todos os campos adicionados.')
                    return None
                if current_type not in allowed_types:
                    messages.error(request, f'Tipo de campo invÃ¡lido: {current_type}.')
                    return None
                fields_data.append({
                    'name': current_label,
                    'type': current_type,
                })
            return fields_data

        def _parse_date_and_time(event_date_raw, event_time_raw, required):
            event_date_raw = (event_date_raw or '').strip()
            event_time_raw = (event_time_raw or '').strip()
            if required and (not event_date_raw or not event_time_raw):
                messages.error(request, 'Data e hora do evento sÃ£o obrigatÃ³rias.')
                return None, None
            if not event_date_raw and not event_time_raw:
                return None, None
            try:
                parsed_date = date.fromisoformat(event_date_raw) if event_date_raw else None
                parsed_time = datetime.strptime(event_time_raw, '%H:%M').time() if event_time_raw else None
            except ValueError:
                messages.error(request, 'Data ou hora do evento invÃ¡lida.')
                return None, None
            return parsed_date, parsed_time

        action = (request.POST.get('action') or '').strip()
        if action == 'create_event':
            name = (request.POST.get('name') or '').strip()
            event_type = (request.POST.get('event_type') or '').strip()
            event_date_raw = (request.POST.get('event_date') or '').strip()
            event_time_raw = (request.POST.get('event_time') or '').strip()
            fields_data = _parse_event_schema()
            if fields_data is None:
                return render(request, self.template_name, self._context(request))

            if not name:
                messages.error(request, 'Informe o nome do evento.')
            else:
                event_date_value, event_time_value = _parse_date_and_time(
                    event_date_raw, event_time_raw, required=True
                )
                if event_date_value is None or event_time_value is None:
                    return render(request, self.template_name, self._context(request))
                Evento.objects.create(
                    name=name,
                    event_type=event_type,
                    event_date=event_date_value,
                    event_time=event_time_value,
                    fields_data=fields_data,
                    created_by=request.user,
                )
                messages.success(request, 'Evento cadastrado com sucesso.')

        elif action == 'save_preset':
            preset_name = (request.POST.get('preset_name') or '').strip()
            event_name = (request.POST.get('name') or '').strip()
            event_type = (request.POST.get('event_type') or '').strip()
            event_date_raw = (request.POST.get('event_date') or '').strip()
            event_time_raw = (request.POST.get('event_time') or '').strip()
            fields_data = _parse_event_schema()
            if fields_data is None:
                return render(request, self.template_name, self._context(request))
            if not preset_name:
                messages.error(request, 'Informe o nome da prÃ©-configuraÃ§Ã£o.')
                return render(request, self.template_name, self._context(request))
            event_date_value, event_time_value = _parse_date_and_time(
                event_date_raw, event_time_raw, required=False
            )
            if (event_date_raw or event_time_raw) and not (event_date_value or event_time_value):
                return render(request, self.template_name, self._context(request))

            EventoPreset.objects.create(
                preset_name=preset_name,
                event_name=event_name,
                event_type=event_type,
                event_date=event_date_value,
                event_time=event_time_value,
                fields_data=fields_data,
                created_by=request.user,
            )
            messages.success(request, 'PrÃ©-configuraÃ§Ã£o salva com sucesso.')

        elif action == 'delete_event':
            event_id = request.POST.get('event_id')
            evento = Evento.objects.filter(pk=event_id).first()
            if not evento:
                messages.error(request, 'Evento nÃ£o encontrado.')
            else:
                if evento.event_date and evento.event_time:
                    event_dt = datetime.combine(evento.event_date, evento.event_time)
                    if timezone.is_naive(event_dt):
                        event_dt = timezone.make_aware(event_dt, timezone.get_current_timezone())
                    if timezone.now() >= event_dt:
                        messages.error(
                            request,
                            'Este evento nÃ£o pode ser excluÃ­do porque a data/hora jÃ¡ foi atingida.',
                        )
                        return render(request, self.template_name, self._context(request))
                evento.delete()
                messages.success(request, 'Evento removido com sucesso.')
        elif action == 'delete_preset':
            preset_id = request.POST.get('preset_id')
            preset = EventoPreset.objects.filter(pk=preset_id).first()
            if not preset:
                messages.error(request, 'PrÃ©-configuraÃ§Ã£o nÃ£o encontrada.')
            else:
                preset.delete()
                messages.success(request, 'PrÃ©-configuraÃ§Ã£o removida com sucesso.')

        return render(request, self.template_name, self._context(request))


class PresencaView(LoginRequiredMixin, View):
    template_name = 'presenca.html'

    def _guard(self, request):
        if not _has_menu_permission(request, 'presenca'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para acessar presenÃ§a.')
            return redirect('accounts:painel')
        return None

    def _relative_event_time_label(self, event_date):
        if not event_date:
            return 'Sem data'
        today = timezone.localdate()
        delta = (event_date - today).days
        if delta == 0:
            return 'Hoje'
        if delta == 1:
            return 'AmanhÃ£'
        if delta == -1:
            return 'Ontem'
        if delta > 1:
            return f'Em {delta} dias'
        return f'HÃ¡ {abs(delta)} dias'

    def _event_status_key(self, event_date):
        if not event_date:
            return 'sem_data'
        today = timezone.localdate()
        delta = (event_date - today).days
        if delta == 0:
            return 'hoje'
        if delta == 1:
            return 'amanha'
        if delta > 1:
            return 'futuro'
        return 'passado'

    def _ordered_events(self):
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        events = list(Evento.objects.select_related('created_by').all())

        def _event_sort_key(evento):
            if evento.event_date == today:
                priority = 0
            elif evento.event_date == tomorrow:
                priority = 1
            elif evento.event_date and evento.event_date > tomorrow:
                priority = 2
            elif evento.event_date:
                priority = 3
            else:
                priority = 4
            return (
                priority,
                evento.event_date or date.max,
                evento.event_time or datetime.max.time(),
                (evento.name or '').lower(),
            )

        events.sort(key=_event_sort_key)
        return events

    def _presence_map(self, evento_id):
        rows = EventoPresenca.objects.filter(evento_id=evento_id).select_related('updated_by')
        data = {}
        for row in rows:
            data[str(row.aventureiro_id)] = {
                'presente': bool(row.presente),
                'updated_at': timezone.localtime(row.updated_at).isoformat(),
                'updated_by': row.updated_by.username if row.updated_by else '',
            }
        return data

    def get(self, request):
        guard = self._guard(request)
        if guard:
            return guard

        eventos = self._ordered_events()
        selected_event = None
        selected_event_id = (request.GET.get('evento') or '').strip()
        if selected_event_id.isdigit():
            selected_event = next((item for item in eventos if item.id == int(selected_event_id)), None)
        if not selected_event and eventos:
            selected_event = eventos[0]

        aventureiros = list(
            Aventureiro.objects
            .select_related('responsavel', 'responsavel__user', 'ficha_completa')
            .order_by('nome')
        )
        for av in aventureiros:
            foto_url = av.foto.url if av.foto else ''
            if not foto_url:
                ficha = getattr(av, 'ficha_completa', None)
                inscricao_data = (ficha.inscricao_data if ficha else {}) or {}
                inline_photo = str(inscricao_data.get('foto_3x4') or '').strip()
                if inline_photo.startswith('data:image/'):
                    foto_url = inline_photo
            av.presenca_foto_url = foto_url
        presencas_map = self._presence_map(selected_event.id) if selected_event else {}
        present_count = sum(1 for value in presencas_map.values() if value.get('presente'))

        event_rows = []
        for evento in eventos:
            event_rows.append({
                'evento': evento,
                'relative_label': self._relative_event_time_label(evento.event_date),
                'status_key': self._event_status_key(evento.event_date),
            })
        selected_event_row = None
        if selected_event:
            selected_event_row = next((row for row in event_rows if row['evento'].id == selected_event.id), None)

        context = {
            'eventos': event_rows,
            'selected_event': selected_event,
            'selected_event_row': selected_event_row,
            'aventureiros': aventureiros,
            'presencas_json': presencas_map,
            'present_count': present_count,
            'total_count': len(aventureiros),
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class PresencaStatusApiView(LoginRequiredMixin, View):
    def get(self, request):
        if not _has_menu_permission(request, 'presenca'):
            return JsonResponse({'ok': False, 'error': 'Sem permissÃ£o para acessar presenÃ§a.'}, status=403)
        event_id_raw = (request.GET.get('evento_id') or '').strip()
        if not event_id_raw.isdigit():
            return JsonResponse({'ok': False, 'error': 'Evento invÃ¡lido.'}, status=400)
        evento = Evento.objects.filter(pk=int(event_id_raw)).first()
        if not evento:
            return JsonResponse({'ok': False, 'error': 'Evento nÃ£o encontrado.'}, status=404)

        rows = EventoPresenca.objects.filter(evento=evento).select_related('updated_by')
        data = {}
        for row in rows:
            data[str(row.aventureiro_id)] = {
                'presente': bool(row.presente),
                'updated_at': timezone.localtime(row.updated_at).isoformat(),
                'updated_by': row.updated_by.username if row.updated_by else '',
            }

        return JsonResponse({
            'ok': True,
            'evento_id': evento.id,
            'presencas': data,
            'present_count': sum(1 for value in data.values() if value.get('presente')),
            'server_time': timezone.localtime(timezone.now()).isoformat(),
        })


class PresencaToggleApiView(LoginRequiredMixin, View):
    def post(self, request):
        if not _has_menu_permission(request, 'presenca'):
            return JsonResponse({'ok': False, 'error': 'Sem permissÃ£o para marcar presenÃ§a.'}, status=403)

        event_id_raw = (request.POST.get('evento_id') or '').strip()
        aventureiro_id_raw = (request.POST.get('aventureiro_id') or '').strip()
        presente_raw = (request.POST.get('presente') or '').strip().lower()
        if not event_id_raw.isdigit() or not aventureiro_id_raw.isdigit():
            return JsonResponse({'ok': False, 'error': 'ParÃ¢metros invÃ¡lidos.'}, status=400)
        if presente_raw not in {'1', '0', 'true', 'false', 'yes', 'no', 'on', 'off'}:
            return JsonResponse({'ok': False, 'error': 'Valor de presenÃ§a invÃ¡lido.'}, status=400)
        presente_value = presente_raw in {'1', 'true', 'yes', 'on'}

        evento = Evento.objects.filter(pk=int(event_id_raw)).first()
        aventureiro = Aventureiro.objects.filter(pk=int(aventureiro_id_raw)).first()
        if not evento or not aventureiro:
            return JsonResponse({'ok': False, 'error': 'Evento ou aventureiro nÃ£o encontrado.'}, status=404)

        presenca, _created = EventoPresenca.objects.update_or_create(
            evento=evento,
            aventureiro=aventureiro,
            defaults={
                'presente': presente_value,
                'updated_by': request.user,
            },
        )
        present_count = EventoPresenca.objects.filter(evento=evento, presente=True).count()
        record_audit(
            action='MarcaÃ§Ã£o de presenÃ§a',
            user=request.user,
            request=request,
            location='PresenÃ§a',
            details=(
                f'Evento="{evento.name}" | Aventureiro="{aventureiro.nome}" | '
                f'Status={"Presente" if presente_value else "Ausente"}'
            ),
        )

        return JsonResponse({
            'ok': True,
            'evento_id': evento.id,
            'aventureiro_id': aventureiro.id,
            'presente': bool(presenca.presente),
            'updated_at': timezone.localtime(presenca.updated_at).isoformat(),
            'updated_by': request.user.username,
            'present_count': present_count,
        })


class AuditoriaView(LoginRequiredMixin, View):
    template_name = 'auditoria.html'

    def get(self, request):
        if not _has_menu_permission(request, 'auditoria'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para acessar auditoria.')
            return redirect('accounts:painel')

        query = (request.GET.get('q') or '').strip()
        user_query = (request.GET.get('usuario') or '').strip()
        action_filter = (request.GET.get('acao') or '').strip()
        location_filter = (request.GET.get('onde') or '').strip()
        subject_filter = (request.GET.get('assunto') or '').strip()
        method_filter = (request.GET.get('metodo') or '').strip().upper()
        date_from = (request.GET.get('data_inicio') or '').strip()
        date_to = (request.GET.get('data_fim') or '').strip()

        logs = AuditLog.objects.select_related('user').all()

        if query:
            logs = logs.filter(
                Q(username__icontains=query)
                | Q(action__icontains=query)
                | Q(location__icontains=query)
                | Q(details__icontains=query)
                | Q(path__icontains=query)
            )
        if user_query:
            logs = logs.filter(username__icontains=user_query)
        if action_filter:
            logs = logs.filter(action=action_filter)
        if location_filter:
            logs = logs.filter(Q(location__icontains=location_filter) | Q(path__icontains=location_filter))
        if subject_filter:
            logs = logs.filter(
                Q(details__icontains=subject_filter)
                | Q(action__icontains=subject_filter)
                | Q(location__icontains=subject_filter)
            )
        if method_filter:
            logs = logs.filter(method=method_filter)
        if date_from:
            logs = logs.filter(created_at__date__gte=date_from)
        if date_to:
            logs = logs.filter(created_at__date__lte=date_to)

        logs = logs.order_by('-created_at')[:500]
        action_options = list(
            AuditLog.objects.exclude(action='').values_list('action', flat=True).distinct().order_by('action')[:200]
        )
        context = {
            'logs': logs,
            'query': query,
            'filters': {
                'usuario': user_query,
                'acao': action_filter,
                'onde': location_filter,
                'assunto': subject_filter,
                'metodo': method_filter,
                'data_inicio': date_from,
                'data_fim': date_to,
            },
            'action_options': action_options,
            'method_options': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class UsuariosView(LoginRequiredMixin, View):
    template_name = 'usuarios.html'

    def get(self, request):
        if not _has_menu_permission(request, 'usuarios'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para acessar usuÃ¡rios.')
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
        if not _has_menu_permission(request, 'permissoes'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para acessar permissÃµes.')
            return redirect('accounts:painel')
        return None

    def _build_context(self, request):
        _ensure_default_access_groups()
        groups = list(AccessGroup.objects.prefetch_related('users').order_by('name'))
        groups_by_id = {group.pk: set(_normalize_menu_keys(group.menu_permissions)) for group in groups}
        accesses = list(
            UserAccess.objects
            .select_related('user', 'user__responsavel', 'user__diretoria')
            .order_by('user__username')
        )
        rows = []
        for access in accesses:
            access = _sync_access_profiles_from_groups(access.user, access=access)
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
                messages.error(request, 'Informe cÃ³digo e nome do grupo.')
            elif AccessGroup.objects.filter(code=code).exists():
                messages.error(request, 'JÃ¡ existe um grupo com esse cÃ³digo.')
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
            messages.success(request, 'PermissÃµes de menu dos grupos atualizadas.')

        elif action == 'save_memberships':
            groups = list(AccessGroup.objects.all())
            users = list(User.objects.all())
            accesses_by_user = {
                access.user_id: access
                for access in UserAccess.objects.select_related('user').all()
            }
            skipped_locked_rows = 0
            for user in users:
                access = accesses_by_user.get(user.pk) or _ensure_user_access(user)
                if _normalize_menu_keys(access.menu_allow):
                    skipped_locked_rows += 1
                    continue
                selected_group_ids = []
                for group in groups:
                    if request.POST.get(f'ug{user.pk}_{group.pk}'):
                        selected_group_ids.append(group.pk)
                user.access_groups.set(selected_group_ids)
                _sync_access_profiles_from_groups(user)
            messages.success(request, 'VÃ­nculo de usuÃ¡rios e grupos atualizado.')

            if skipped_locked_rows:
                messages.info(request, f'{skipped_locked_rows} linha(s) ignorada(s) por exceÃ§Ã£o individual ativa.')

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
            messages.success(request, 'PermissÃµes por usuÃ¡rio atualizadas.')

        elif action == 'delete_group':
            group_id = request.POST.get('group_id')
            group = AccessGroup.objects.filter(pk=group_id).first()
            if not group:
                messages.error(request, 'Grupo nÃ£o encontrado.')
            elif group.code in {'diretor', 'diretoria', 'responsavel', 'professor'}:
                messages.error(request, 'NÃ£o Ã© possÃ­vel excluir grupos padrÃ£o.')
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
        if not _has_menu_permission(request, 'documentos_inscricao'):
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
                messages.error(request, 'Selecione um aventureiro vÃ¡lido para gerar o documento.')
                return redirect(request.path)
            if doc_type not in {item[0] for item in DocumentoInscricaoGerado.TYPE_CHOICES}:
                messages.error(request, 'Selecione um tipo de documento vÃ¡lido.')
                return redirect(request.path)
            ficha = getattr(aventureiro, 'ficha_completa', None)
            if not ficha:
                messages.error(request, 'Esse aventureiro ainda nÃ£o possui as fichas completas salvas.')
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
                messages.error(request, 'Documento gerado nÃ£o encontrado.')
                return redirect(request.path)
            documento.delete()
            messages.success(request, 'Documento gerado excluÃ­do com sucesso.')
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
                messages.error(request, 'Template nÃ£o encontrado.')
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
        if not _has_menu_permission(request, 'documentos_inscricao'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para visualizar documentos gerados.')
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
        if not _has_menu_permission(request, 'documentos_inscricao'):
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
        if not _has_menu_permission(request, 'whatsapp'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para acessar WhatsApp.')
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
        confirmacao_template = get_template_message(WhatsAppTemplate.TYPE_CONFIRMACAO)
        financeiro_template = get_template_message(WhatsAppTemplate.TYPE_FINANCEIRO)
        teste_template = get_template_message(WhatsAppTemplate.TYPE_TESTE)
        context = {
            'rows': self._users_context(),
            'queue': queue_stats(),
            'cadastro_template': cadastro_template,
            'diretoria_template': diretoria_template,
            'confirmacao_template': confirmacao_template,
            'financeiro_template': financeiro_template,
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
        financeiro_enabled = []
        for row in rows:
            user = row['user']
            pref = row['pref']
            prefix = f'u{user.pk}'
            pref.phone_number = normalize_phone_number(request.POST.get(f'{prefix}_phone', '').strip())
            pref.notify_cadastro = bool(request.POST.get(f'{prefix}_cadastro'))
            pref.notify_diretoria = bool(request.POST.get(f'{prefix}_diretoria'))
            pref.notify_financeiro = bool(request.POST.get(f'{prefix}_financeiro'))
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
            if pref.notify_financeiro:
                financeiro_enabled.append(user.username)
        WhatsAppTemplate.objects.update_or_create(
            notification_type=WhatsAppTemplate.TYPE_CADASTRO,
            defaults={'message_text': request.POST.get('template_cadastro', '').strip()},
        )
        WhatsAppTemplate.objects.update_or_create(
            notification_type=WhatsAppTemplate.TYPE_DIRETORIA,
            defaults={'message_text': request.POST.get('template_diretoria', '').strip()},
        )
        WhatsAppTemplate.objects.update_or_create(
            notification_type=WhatsAppTemplate.TYPE_CONFIRMACAO,
            defaults={'message_text': request.POST.get('template_confirmacao', '').strip()},
        )
        WhatsAppTemplate.objects.update_or_create(
            notification_type=WhatsAppTemplate.TYPE_FINANCEIRO,
            defaults={'message_text': request.POST.get('template_financeiro', '').strip()},
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
                    'confirmacao_template': get_template_message(WhatsAppTemplate.TYPE_CONFIRMACAO),
                    'financeiro_template': get_template_message(WhatsAppTemplate.TYPE_FINANCEIRO),
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
                f'PreferÃªncias salvas. Testes enviados: {sent_count}. Falhas: {failed_count}.',
            )
            if failed_items:
                messages.error(request, 'Falhas: ' + ' | '.join(failed_items[:3]))
        else:
            messages.success(request, 'PreferÃªncias de notificaÃ§Ã£o salvas com sucesso.')

        if cadastro_enabled:
            preview = ', '.join(cadastro_enabled[:6])
            suffix = '...' if len(cadastro_enabled) > 6 else ''
            messages.info(
                request,
                f'Cadastro marcado para: {preview}{suffix}',
            )
        else:
            messages.info(request, 'Nenhum contato estÃ¡ marcado para receber notificaÃ§Ã£o de Cadastro.')
        if diretoria_enabled:
            preview = ', '.join(diretoria_enabled[:6])
            suffix = '...' if len(diretoria_enabled) > 6 else ''
            messages.info(
                request,
                f'Diretoria marcado para: {preview}{suffix}',
            )
        else:
            messages.info(request, 'Nenhum contato estÃ¡ marcado para receber notificaÃ§Ã£o de Diretoria.')
        if financeiro_enabled:
            preview = ', '.join(financeiro_enabled[:6])
            suffix = '...' if len(financeiro_enabled) > 6 else ''
            messages.info(request, f'Pagamento aprovado marcado para: {preview}{suffix}')
        else:
            messages.info(request, 'Nenhum contato estÃ¡ marcado para receber notificaÃ§Ã£o de Pagamento aprovado.')
        context = {
            'rows': self._users_context(),
            'queue': queue_stats(),
            'cadastro_template': get_template_message(WhatsAppTemplate.TYPE_CADASTRO),
            'diretoria_template': get_template_message(WhatsAppTemplate.TYPE_DIRETORIA),
            'confirmacao_template': get_template_message(WhatsAppTemplate.TYPE_CONFIRMACAO),
            'financeiro_template': get_template_message(WhatsAppTemplate.TYPE_FINANCEIRO),
            'teste_template': get_template_message(WhatsAppTemplate.TYPE_TESTE),
        }
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class FinanceiroView(LoginRequiredMixin, View):
    template_name = 'financeiro.html'

    def _guard(self, request):
        if not _has_menu_permission(request, 'financeiro'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para acessar Financeiro.')
            return redirect('accounts:painel')
        return None

    def _month_label(self, month):
        labels = {
            1: 'Janeiro',
            2: 'Fevereiro',
            3: 'MarÃ§o',
            4: 'Abril',
            5: 'Maio',
            6: 'Junho',
            7: 'Julho',
            8: 'Agosto',
            9: 'Setembro',
            10: 'Outubro',
            11: 'Novembro',
            12: 'Dezembro',
        }
        return labels.get(month, str(month))

    def _parse_valor(self, raw_value):
        raw = str(raw_value or '').strip()
        if not raw:
            return Decimal('35.00')
        normalized = raw.replace('R$', '').replace(' ', '')
        if ',' in normalized and '.' in normalized:
            normalized = normalized.replace('.', '').replace(',', '.')
        else:
            normalized = normalized.replace(',', '.')
        try:
            value = Decimal(normalized)
        except (InvalidOperation, ValueError):
            return None
        if value <= 0:
            return None
        return value.quantize(Decimal('0.01'))

    def _format_currency(self, value):
        try:
            decimal_value = Decimal(value).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError, TypeError):
            decimal_value = Decimal('0.00')
        text = f'{decimal_value:,.2f}'
        return 'R$ ' + text.replace(',', 'X').replace('.', ',').replace('X', '.')

    def _aventureiros(self):
        return list(
            Aventureiro.objects
            .select_related('responsavel', 'responsavel__user')
            .order_by('nome')
        )

    def _is_responsavel_mode(self, request):
        return _get_active_profile(request) == UserAccess.ROLE_RESPONSAVEL

    def _mp_access_token(self):
        return (
            os.getenv('MP_ACCESS_TOKEN_PROD', '').strip()
            or os.getenv('MP_ACCESS_TOKEN', '').strip()
        )

    def _mp_api_request(self, method, path, payload=None):
        token = self._mp_access_token()
        if not token:
            raise ValueError('MP_ACCESS_TOKEN_PROD nÃƒÂ£o configurado no servidor.')

        url = f'https://api.mercadopago.com{path}'
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
        }
        data = None
        if payload is not None:
            headers['Content-Type'] = 'application/json'
            headers['X-Idempotency-Key'] = hashlib.sha256(os.urandom(16)).hexdigest()
            data = json.dumps(payload).encode('utf-8')

        req = urllib_request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with urllib_request.urlopen(req, timeout=30) as response:
                body = response.read().decode('utf-8')
                return json.loads(body) if body else {}
        except urllib_error.HTTPError as exc:
            try:
                body = exc.read().decode('utf-8')
                details = json.loads(body)
                message = details.get('message') or details.get('error') or body
            except Exception:
                message = str(exc)
            raise ValueError(f'Erro Mercado Pago: {message}') from exc

    def _mp_notification_url(self, request):
        explicit = os.getenv('MP_NOTIFICATION_URL', '').strip()
        if explicit:
            return explicit
        try:
            return request.build_absolute_uri('/accounts/financeiro/mp-webhook/')
        except Exception:
            return ''

    def _mp_status_label(self, pagamento):
        if pagamento.status == PagamentoMensalidade.STATUS_PAGO:
            return 'Pagamento aprovado'
        status = (pagamento.mp_status or '').lower()
        status_map = {
            'pending': 'Aguardando pagamento',
            'in_process': 'Processando pagamento',
            'approved': 'Pagamento aprovado',
            'rejected': 'Pagamento recusado',
            'cancelled': 'Pagamento cancelado',
        }
        return status_map.get(status, 'Aguardando pagamento')

    def _mp_payer_email(self, request, pagamento):
        candidate_emails = []
        if getattr(request.user, 'email', ''):
            candidate_emails.append(request.user.email.strip())
        if getattr(pagamento.responsavel, 'responsavel_email', ''):
            candidate_emails.append(pagamento.responsavel.responsavel_email.strip())
        if getattr(pagamento.responsavel, 'mae_email', ''):
            candidate_emails.append(pagamento.responsavel.mae_email.strip())
        if getattr(pagamento.responsavel, 'pai_email', ''):
            candidate_emails.append(pagamento.responsavel.pai_email.strip())

        for email in candidate_emails:
            if not email:
                continue
            try:
                validate_email(email)
            except ValidationError:
                continue
            return email

        domain = (
            os.getenv('MP_PAYER_EMAIL_DOMAIN', '').strip()
            or os.getenv('SITE_DOMAIN', '').strip()
            or request.get_host().split(':')[0].strip()
            or 'pinhaljunior.com.br'
        )
        domain = domain.lower().replace('http://', '').replace('https://', '').strip('/')
        if not domain or '.' not in domain:
            domain = 'pinhaljunior.com.br'
        return f'mensalidade{pagamento.pk}.{request.user.id}@{domain}'

    def _create_mp_pix_payment(self, request, pagamento):
        responsible_name = (
            pagamento.responsavel.responsavel_nome
            or pagamento.responsavel.mae_nome
            or pagamento.responsavel.pai_nome
            or request.user.get_full_name()
            or request.user.username
        ).strip()
        name_parts = [part for part in responsible_name.split() if part]
        first_name = (name_parts[0] if name_parts else request.user.username)[:60]
        last_name = (' '.join(name_parts[1:]) if len(name_parts) > 1 else 'Responsavel')[:60]
        payer_email = self._mp_payer_email(request, pagamento)
        external_reference = f'MENSALIDADE_{pagamento.pk}'
        payload = {
            'transaction_amount': float(pagamento.valor_total),
            'description': f'Mensalidades aventureiros - Pagamento #{pagamento.pk}',
            'payment_method_id': 'pix',
            'external_reference': external_reference,
            'payer': {
                'email': payer_email,
                'first_name': first_name,
                'last_name': last_name,
            },
        }
        notification_url = self._mp_notification_url(request)
        if notification_url:
            payload['notification_url'] = notification_url

        payment = self._mp_api_request('POST', '/v1/payments', payload)
        tx_data = payment.get('point_of_interaction', {}).get('transaction_data', {})
        pix_code = tx_data.get('qr_code', '') or ''
        qr_base64 = tx_data.get('qr_code_base64', '') or ''
        if not pix_code or not qr_base64:
            raise ValueError('Mercado Pago nÃƒÂ£o retornou QR Code Pix para este pagamento.')
        return {
            'payment_id': str(payment.get('id') or ''),
            'external_reference': external_reference,
            'status': (payment.get('status') or '').lower(),
            'status_detail': payment.get('status_detail') or '',
            'pix_code': pix_code,
            'qr_base64': qr_base64,
        }

    def _get_mp_payment(self, payment_id):
        return self._mp_api_request('GET', f'/v1/payments/{payment_id}')

    def _sync_pagamento_from_mp(self, pagamento, payment_data):
        was_paid = pagamento.status == PagamentoMensalidade.STATUS_PAGO
        mp_status = (payment_data.get('status') or '').lower()
        mp_status_detail = payment_data.get('status_detail') or ''
        mp_payment_id = str(payment_data.get('id') or pagamento.mp_payment_id or '')
        mp_external_reference = payment_data.get('external_reference') or pagamento.mp_external_reference
        update_fields = []

        if mp_payment_id != pagamento.mp_payment_id:
            pagamento.mp_payment_id = mp_payment_id
            update_fields.append('mp_payment_id')
        if (mp_external_reference or '') != pagamento.mp_external_reference:
            pagamento.mp_external_reference = mp_external_reference or ''
            update_fields.append('mp_external_reference')
        if mp_status != pagamento.mp_status:
            pagamento.mp_status = mp_status
            update_fields.append('mp_status')
        if mp_status_detail != pagamento.mp_status_detail:
            pagamento.mp_status_detail = mp_status_detail
            update_fields.append('mp_status_detail')

        target_status = pagamento.status
        if mp_status == 'approved':
            target_status = PagamentoMensalidade.STATUS_PAGO
        elif mp_status in {'pending'}:
            target_status = PagamentoMensalidade.STATUS_PENDENTE
        elif mp_status in {'in_process'}:
            target_status = PagamentoMensalidade.STATUS_PROCESSANDO
        elif mp_status in {'cancelled'}:
            target_status = PagamentoMensalidade.STATUS_CANCELADO
        elif mp_status in {'rejected'}:
            target_status = PagamentoMensalidade.STATUS_FALHA
        if target_status != pagamento.status:
            pagamento.status = target_status
            update_fields.append('status')

        if mp_status == 'approved' and not pagamento.paid_at:
            pagamento.paid_at = timezone.now()
            update_fields.append('paid_at')
        elif mp_status != 'approved' and pagamento.paid_at:
            pagamento.paid_at = None
            update_fields.append('paid_at')

        if update_fields:
            pagamento.save(update_fields=list(dict.fromkeys(update_fields)))

        if mp_status == 'approved':
            pagamento.mensalidades.filter(status=MensalidadeAventureiro.STATUS_PENDENTE).update(
                status=MensalidadeAventureiro.STATUS_PAGA
            )
            if not was_paid:
                self._send_whatsapp_pagamento_aprovado(pagamento)

    def _pix_modal_context(self, pagamento):
        return {
            'id': pagamento.pk,
            'payment_id': pagamento.mp_payment_id,
            'status': pagamento.status,
            'status_label': self._mp_status_label(pagamento),
            'valor_total': self._format_currency(pagamento.valor_total),
            'qr_base64': pagamento.mp_qr_code_base64,
            'pix_code': pagamento.mp_qr_code,
        }

    def _send_whatsapp_pagamento_aprovado(self, pagamento):
        if pagamento.whatsapp_notified_at:
            return

        mensalidades = list(
            pagamento.mensalidades.select_related('aventureiro').order_by('aventureiro__nome', 'ano_referencia', 'mes_referencia')
        )
        if not mensalidades:
            return

        responsavel_user = pagamento.responsavel.user
        responsavel_nome = (
            pagamento.responsavel.responsavel_nome
            or pagamento.responsavel.mae_nome
            or pagamento.responsavel.pai_nome
            or responsavel_user.get_full_name()
            or responsavel_user.username
        ).strip()
        mensalidades_text = '\n'.join(
            f"- {item.aventureiro.nome} - {item.get_tipo_display()} - {self._month_label(item.mes_referencia)}/{item.ano_referencia} ({self._format_currency(item.valor)})"
            for item in mensalidades
        )
        payload = {
            'responsavel_nome': responsavel_nome or responsavel_user.username,
            'mensalidades': mensalidades_text,
            'valor_total': self._format_currency(pagamento.valor_total),
            'pagamento_id': pagamento.mp_payment_id or str(pagamento.pk),
            'data_hora': timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M:%S'),
        }
        message_text = render_message(get_template_message(WhatsAppTemplate.TYPE_FINANCEIRO), payload)

        recipients = []
        seen_phones = set()

        def add_recipient(user, force_send=False):
            pref, _ = WhatsAppPreference.objects.get_or_create(user=user)
            phone_number = normalize_phone_number(pref.phone_number or resolve_user_phone(user))
            if not phone_number or phone_number in seen_phones:
                return
            seen_phones.add(phone_number)
            recipients.append((user, phone_number, force_send))

        add_recipient(responsavel_user, force_send=True)
        extras = (
            UserAccess.objects
            .select_related('user')
            .filter(user__whatsapp_preference__notify_financeiro=True)
            .order_by('user__username')
        )
        for access in extras:
            add_recipient(access.user, force_send=False)

        if not recipients:
            pagamento.whatsapp_notified_at = timezone.now()
            pagamento.save(update_fields=['whatsapp_notified_at', 'updated_at'])
            return

        sent_any = False
        for user, phone_number, _force_send in recipients:
            queue_item = WhatsAppQueue.objects.create(
                user=user,
                phone_number=phone_number,
                notification_type=WhatsAppQueue.TYPE_FINANCEIRO,
                message_text=message_text,
                status=WhatsAppQueue.STATUS_PENDING,
            )
            success, provider_id, error_message = send_wapi_text(phone_number, message_text)
            queue_item.attempts = 1
            if success:
                queue_item.status = WhatsAppQueue.STATUS_SENT
                queue_item.provider_message_id = provider_id
                queue_item.sent_at = timezone.now()
                queue_item.last_error = ''
                sent_any = True
            else:
                queue_item.status = WhatsAppQueue.STATUS_FAILED
                queue_item.last_error = error_message
            queue_item.save(
                update_fields=['status', 'attempts', 'provider_message_id', 'sent_at', 'last_error']
            )

        if sent_any:
            pagamento.whatsapp_notified_at = timezone.now()
            pagamento.save(update_fields=['whatsapp_notified_at', 'updated_at'])

    def _mensalidades_responsavel_context(self, request):
        hoje = timezone.localdate()
        responsavel = getattr(request.user, 'responsavel', None)
        rows = []
        if responsavel:
            aventureiros = list(
                Aventureiro.objects
                .filter(responsavel=responsavel)
                .order_by('nome')
            )
            if aventureiros:
                itens = (
                    MensalidadeAventureiro.objects
                    .filter(
                        aventureiro__in=aventureiros,
                        status=MensalidadeAventureiro.STATUS_PENDENTE,
                    )
                    .filter(
                        Q(ano_referencia__lt=hoje.year)
                        | Q(ano_referencia=hoje.year, mes_referencia__lte=hoje.month)
                    )
                    .select_related('aventureiro')
                    .order_by('aventureiro__nome', 'ano_referencia', 'mes_referencia')
                )
                rows_map = {
                    av.pk: {
                        'aventureiro_id': av.pk,
                        'aventureiro_nome': av.nome,
                        'mensalidades': [],
                    }
                    for av in aventureiros
                }
                for item in itens:
                    rows_map[item.aventureiro_id]['mensalidades'].append({
                        'id': item.pk,
                        'competencia': f'{item.get_tipo_display()} - {self._month_label(item.mes_referencia)}/{item.ano_referencia}',
                        'tipo': item.tipo,
                        'tipo_label': item.get_tipo_display(),
                        'valor': self._format_currency(item.valor),
                        'is_atrasada': (item.ano_referencia < hoje.year) or (item.ano_referencia == hoje.year and item.mes_referencia < hoje.month),
                    })
                rows = [row for row in rows_map.values() if row['mensalidades']]
        return {
            'financeiro_mode': 'responsavel',
            'responsavel_rows': rows,
            'responsavel_tem_aventureiros': bool(getattr(request.user, 'responsavel', None) and request.user.responsavel.aventures.exists()),
            'mes_atual_label': self._month_label(hoje.month),
            'ano_atual': hoje.year,
            'responsavel_pix_pagamento': None,
        }

    def _mensalidades_context(self, aventureiro_id='', valor_mensalidade='35'):
        aventureiros = self._aventureiros()
        selected_id = str(aventureiro_id or '').strip()
        selected = None
        if selected_id.isdigit():
            selected = next((av for av in aventureiros if av.pk == int(selected_id)), None)
        mensalidades = []
        if selected:
            registros = (
                MensalidadeAventureiro.objects
                .filter(aventureiro=selected)
                .order_by('ano_referencia', 'mes_referencia')
            )
            for item in registros:
                mensalidades.append({
                    'id': item.pk,
                    'competencia': f'{item.get_tipo_display()} - {self._month_label(item.mes_referencia)}/{item.ano_referencia}',
                    'tipo': item.tipo,
                    'tipo_label': item.get_tipo_display(),
                    'status_code': item.status,
                    'status': item.get_status_display(),
                    'valor': self._format_currency(item.valor),
                    'valor_raw': f'{Decimal(item.valor).quantize(Decimal("0.01"))}',
                    'mes': item.mes_referencia,
                    'ano': item.ano_referencia,
                })
        ano_resumo = timezone.localdate().year
        resumo_rows_map = {}
        resumo_qs = (
            MensalidadeAventureiro.objects
            .select_related('aventureiro', 'aventureiro__responsavel', 'aventureiro__responsavel__user')
            .filter(ano_referencia=ano_resumo)
            .order_by('aventureiro__nome', 'mes_referencia')
        )
        for item in resumo_qs:
            key = item.aventureiro_id
            row = resumo_rows_map.get(key)
            if row is None:
                resp_user = getattr(getattr(item.aventureiro, 'responsavel', None), 'user', None)
                row = {
                    'aventureiro_id': item.aventureiro_id,
                    'aventureiro_nome': item.aventureiro.nome,
                    'responsavel_username': resp_user.username if resp_user else '',
                    'cells': [{'id': '', 'label': '-', 'valor_raw': '', 'competencia': '', 'status': '', 'filled': False} for _ in range(12)],
                }
                resumo_rows_map[key] = row
            row['cells'][item.mes_referencia - 1] = {
                'id': item.pk,
                'label': self._format_currency(item.valor),
                'valor_raw': f'{Decimal(item.valor).quantize(Decimal("0.01"))}',
                'competencia': f'{item.get_tipo_display()} - {self._month_label(item.mes_referencia)}/{item.ano_referencia}',
                'tipo': item.tipo,
                'tipo_label': item.get_tipo_display(),
                'status_code': item.status,
                'status': item.get_status_display(),
                'filled': True,
            }
        return {
            'aventureiros': aventureiros,
            'selected_aventureiro': selected,
            'selected_aventureiro_id': selected_id,
            'mensalidades': mensalidades,
            'valor_mensalidade': str(valor_mensalidade or '35'),
            'resumo_ano': ano_resumo,
            'resumo_meses': [self._month_label(m)[:3] for m in range(1, 13)],
            'resumo_rows': list(resumo_rows_map.values()),
        }

    def get(self, request):
        guard = self._guard(request)
        if guard:
            return guard
        if self._is_responsavel_mode(request):
            context = self._mensalidades_responsavel_context(request)
        else:
            context = self._mensalidades_context(
                request.GET.get('aventureiro'),
                request.GET.get('valor', '35'),
            )
        context.update({
            'active_financeiro_tab': 'mensalidades',
        })
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)

    def post(self, request):
        guard = self._guard(request)
        if guard:
            return guard
        if self._is_responsavel_mode(request):
            action = str(request.POST.get('action') or '').strip()
            context = self._mensalidades_responsavel_context(request)
            responsavel = getattr(request.user, 'responsavel', None)
            if action == 'pagar_mensalidades':
                selected_ids = []
                for raw in request.POST.getlist('mensalidades_ids'):
                    text = str(raw or '').strip()
                    if text.isdigit():
                        selected_ids.append(int(text))
                selected_ids = list(dict.fromkeys(selected_ids))
                if not responsavel:
                    messages.error(request, 'UsuÃ¡rio nÃ£o possui cadastro de responsÃ¡vel vinculado.')
                elif not selected_ids:
                    messages.error(request, 'Selecione pelo menos uma mensalidade para pagar.')
                else:
                    hoje = timezone.localdate()
                    mensalidades_qs = (
                        MensalidadeAventureiro.objects
                        .select_related('aventureiro')
                        .filter(
                            pk__in=selected_ids,
                            aventureiro__responsavel=responsavel,
                            status=MensalidadeAventureiro.STATUS_PENDENTE,
                        )
                        .filter(
                            Q(ano_referencia__lt=hoje.year)
                            | Q(ano_referencia=hoje.year, mes_referencia__lte=hoje.month)
                        )
                        .order_by('aventureiro__nome', 'ano_referencia', 'mes_referencia')
                    )
                    mensalidades = list(mensalidades_qs)
                    if len(mensalidades) != len(selected_ids):
                        messages.error(request, 'Algumas mensalidades selecionadas sÃ£o invÃ¡lidas ou nÃ£o pertencem ao responsÃ¡vel logado.')
                    else:
                        total = sum((item.valor for item in mensalidades), Decimal('0.00')).quantize(Decimal('0.01'))
                        try:
                            with transaction.atomic():
                                pagamento = PagamentoMensalidade.objects.create(
                                    responsavel=responsavel,
                                    valor_total=total,
                                    created_by=request.user,
                                    status=PagamentoMensalidade.STATUS_PENDENTE,
                                )
                                pagamento.mensalidades.set(mensalidades)
                                mp_payload = self._create_mp_pix_payment(request, pagamento)
                                pagamento.mp_payment_id = mp_payload['payment_id']
                                pagamento.mp_external_reference = mp_payload['external_reference']
                                pagamento.mp_status = mp_payload['status']
                                pagamento.mp_status_detail = mp_payload['status_detail']
                                pagamento.mp_qr_code = mp_payload['pix_code']
                                pagamento.mp_qr_code_base64 = mp_payload['qr_base64']
                                if mp_payload['status'] == 'approved':
                                    pagamento.status = PagamentoMensalidade.STATUS_PAGO
                                    pagamento.paid_at = timezone.now()
                                elif mp_payload['status'] == 'in_process':
                                    pagamento.status = PagamentoMensalidade.STATUS_PROCESSANDO
                                else:
                                    pagamento.status = PagamentoMensalidade.STATUS_PENDENTE
                                pagamento.save(update_fields=[
                                    'mp_payment_id', 'mp_external_reference', 'mp_status', 'mp_status_detail',
                                    'mp_qr_code', 'mp_qr_code_base64', 'status', 'paid_at', 'updated_at',
                                ])
                                if pagamento.mp_status == 'approved':
                                    pagamento.mensalidades.filter(status=MensalidadeAventureiro.STATUS_PENDENTE).update(
                                        status=MensalidadeAventureiro.STATUS_PAGA
                                    )
                                    self._send_whatsapp_pagamento_aprovado(pagamento)
                        except ValueError as exc:
                            messages.error(request, str(exc))
                        except Exception:
                            messages.error(request, 'NÃ£o foi possÃ­vel iniciar o pagamento no Mercado Pago agora.')
                        else:
                            if pagamento.status == PagamentoMensalidade.STATUS_PAGO:
                                messages.success(request, 'Pagamento aprovado e mensalidades marcadas como pagas.')
                            else:
                                messages.success(request, 'Pagamento Pix gerado com sucesso. Use o QR Code para concluir.')
                            context = self._mensalidades_responsavel_context(request)
                            context['responsavel_pix_pagamento'] = self._pix_modal_context(pagamento)
            context.update({'active_financeiro_tab': 'mensalidades'})
            context.update(_sidebar_context(request))
            return render(request, self.template_name, context)
        action = str(request.POST.get('action') or '').strip()
        aventureiro_id = str(request.POST.get('aventureiro_id') or '').strip()
        valor_input = str(request.POST.get('valor_mensalidade') or '35').strip()
        if action == 'gerar_mensalidades':
            aventureiro = Aventureiro.objects.filter(pk=aventureiro_id).select_related('responsavel', 'responsavel__user').first()
            if not aventureiro:
                messages.error(request, 'Selecione um aventureiro para gerar mensalidades.')
            else:
                valor = self._parse_valor(valor_input)
                if valor is None:
                    messages.error(request, 'Informe um valor vÃ¡lido para a mensalidade.')
                    context = self._mensalidades_context(aventureiro_id, valor_input)
                    context.update({'active_financeiro_tab': 'mensalidades'})
                    context.update(_sidebar_context(request))
                    return render(request, self.template_name, context)
                result = _generate_financeiro_entries_for_aventureiro(
                    aventureiro,
                    created_by=request.user,
                    valor=valor,
                )
                if result['created_count']:
                    messages.success(
                        request,
                        (
                            f'Cobranças geradas para {aventureiro.nome}: {result["created_count"]} registro(s) '
                            f'({result["created_inscricao"]} inscrição + {result["created_mensalidades"]} mensalidades).'
                        ),
                    )
                else:
                    messages.info(request, f'As cobranças de {aventureiro.nome} já estavam geradas até dezembro deste ano.')
        elif action == 'gerar_mensalidades_todos':
            valor = self._parse_valor(valor_input)
            if valor is None:
                messages.error(request, 'Informe um valor válido para gerar as mensalidades de todos.')
            else:
                aventureiros = self._aventureiros()
                total_created = 0
                total_inscricao = 0
                total_mensalidades = 0
                affected = 0
                for av in aventureiros:
                    result = _generate_financeiro_entries_for_aventureiro(
                        av,
                        created_by=request.user,
                        valor=valor,
                    )
                    if result['created_count']:
                        affected += 1
                        total_created += result['created_count']
                        total_inscricao += result['created_inscricao']
                        total_mensalidades += result['created_mensalidades']
                if total_created:
                    messages.success(
                        request,
                        (
                            f'Cobranças geradas para todos: {total_created} registro(s) em {affected} aventureiro(s) '
                            f'({total_inscricao} inscrição + {total_mensalidades} mensalidades).'
                        ),
                    )
                else:
                    messages.info(request, 'Todos os aventureiros já possuem as cobranças geradas até dezembro deste ano.')

        elif action == 'editar_mensalidade':
            mensalidade_id = str(request.POST.get('mensalidade_id') or '').strip()
            valor_edicao_input = str(request.POST.get('valor_mensalidade_edicao') or '').strip()
            mensalidade = (
                MensalidadeAventureiro.objects
                .select_related('aventureiro')
                .filter(pk=mensalidade_id)
                .first()
            )
            if not mensalidade:
                messages.error(request, 'Mensalidade nÃƒÂ£o encontrada para ediÃƒÂ§ÃƒÂ£o.')
            else:
                aventureiro_id = str(mensalidade.aventureiro_id)
                valor = self._parse_valor(valor_edicao_input)
                if valor is None:
                    messages.error(request, 'Informe um valor vÃƒÂ¡lido para editar a mensalidade.')
                else:
                    mensalidade.valor = valor
                    mensalidade.save(update_fields=['valor', 'updated_at'])
                    messages.success(
                        request,
                        f'Mensalidade {self._month_label(mensalidade.mes_referencia)}/{mensalidade.ano_referencia} atualizada para {self._format_currency(valor)}.',
                    )
        elif action == 'excluir_mensalidade':
            mensalidade_id = str(request.POST.get('mensalidade_id') or '').strip()
            mensalidade = (
                MensalidadeAventureiro.objects
                .select_related('aventureiro')
                .filter(pk=mensalidade_id)
                .first()
            )
            if not mensalidade:
                messages.error(request, 'Mensalidade nÃƒÂ£o encontrada para exclusÃƒÂ£o.')
            else:
                aventureiro_id = str(mensalidade.aventureiro_id)
                competencia = f'{self._month_label(mensalidade.mes_referencia)}/{mensalidade.ano_referencia}'
                aventura_nome = mensalidade.aventureiro.nome
                mensalidade.delete()
                messages.success(request, f'Mensalidade {competencia} de {aventura_nome} excluÃƒÂ­da com sucesso.')
        elif action in {'marcar_mensalidade_paga', 'marcar_mensalidade_pendente'}:
            mensalidade_id = str(request.POST.get('mensalidade_id') or '').strip()
            mensalidade = (
                MensalidadeAventureiro.objects
                .select_related('aventureiro')
                .filter(pk=mensalidade_id)
                .first()
            )
            if not mensalidade:
                messages.error(request, 'Mensalidade nÃƒÂ£o encontrada para atualizar status.')
            else:
                aventureiro_id = str(mensalidade.aventureiro_id)
                novo_status = (
                    MensalidadeAventureiro.STATUS_PAGA
                    if action == 'marcar_mensalidade_paga'
                    else MensalidadeAventureiro.STATUS_PENDENTE
                )
                if mensalidade.status == novo_status:
                    messages.info(request, f'Mensalidade jÃƒÂ¡ estÃƒÂ¡ como {mensalidade.get_status_display().lower()}.')
                else:
                    mensalidade.status = novo_status
                    mensalidade.save(update_fields=['status', 'updated_at'])
                    messages.success(
                        request,
                        f'Mensalidade {self._month_label(mensalidade.mes_referencia)}/{mensalidade.ano_referencia} marcada como {mensalidade.get_status_display().lower()}.',
                    )

        context = self._mensalidades_context(aventureiro_id, valor_input)
        context.update({
            'active_financeiro_tab': 'mensalidades',
        })
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class PagamentoMensalidadeStatusApiView(LoginRequiredMixin, View):
    def get(self, request, pk):
        pagamento = get_object_or_404(
            PagamentoMensalidade.objects.select_related('responsavel', 'responsavel__user'),
            pk=pk,
        )
        if not _has_menu_permission(request, 'financeiro'):
            return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

        active_profile = _get_active_profile(request)
        if active_profile == UserAccess.ROLE_RESPONSAVEL:
            responsavel = getattr(request.user, 'responsavel', None)
            if not responsavel or pagamento.responsavel_id != responsavel.pk:
                return JsonResponse({'ok': False, 'error': 'forbidden'}, status=403)

        view = FinanceiroView()
        if pagamento.mp_payment_id and pagamento.status != PagamentoMensalidade.STATUS_PAGO:
            try:
                payment_data = view._get_mp_payment(pagamento.mp_payment_id)
                view._sync_pagamento_from_mp(pagamento, payment_data)
                pagamento.refresh_from_db()
            except Exception:
                pass

        return JsonResponse({
            'ok': True,
            'pagamento_id': pagamento.pk,
            'status': pagamento.status,
            'status_label': view._mp_status_label(pagamento),
            'mp_status': pagamento.mp_status,
            'mp_status_detail': pagamento.mp_status_detail,
            'is_paid': pagamento.status == PagamentoMensalidade.STATUS_PAGO,
        })


@method_decorator(csrf_exempt, name='dispatch')
class PagamentoMensalidadeWebhookView(View):
    def _extract_payment_id(self, request):
        payment_id = request.GET.get('data.id') or request.GET.get('id')
        if payment_id:
            return str(payment_id)

        try:
            payload = json.loads((request.body or b'').decode('utf-8') or '{}')
        except json.JSONDecodeError:
            payload = {}

        if isinstance(payload, dict):
            data = payload.get('data', {})
            if isinstance(data, dict) and data.get('id'):
                return str(data['id'])
            if payload.get('id'):
                return str(payload['id'])
        return ''

    def _is_valid_signature(self, request, payment_id):
        secret = os.getenv('MP_WEBHOOK_SECRET', '').strip()
        if not secret:
            return True

        signature = request.headers.get('x-signature', '')
        request_id = request.headers.get('x-request-id', '')
        if not signature or not request_id:
            return False

        ts_value = ''
        v1_value = ''
        for part in signature.split(','):
            key, _, value = part.strip().partition('=')
            if key == 'ts':
                ts_value = value
            elif key == 'v1':
                v1_value = value

        if not ts_value or not v1_value:
            return False

        manifest = f'id:{payment_id};request-id:{request_id};ts:{ts_value};'
        expected = hmac.new(secret.encode('utf-8'), manifest.encode('utf-8'), hashlib.sha256).hexdigest()
        return constant_time_compare(expected, v1_value)

    def _sync_by_payment_id(self, payment_id):
        view = FinanceiroView()
        payment_data = view._get_mp_payment(payment_id)
        external_reference = str(payment_data.get('external_reference') or '').strip()
        pagamento = PagamentoMensalidade.objects.filter(mp_payment_id=str(payment_id)).first()
        if not pagamento and external_reference:
            pagamento = PagamentoMensalidade.objects.filter(mp_external_reference=external_reference).first()
        if not pagamento:
            return False, 'payment_not_found_locally'
        view._sync_pagamento_from_mp(pagamento, payment_data)
        return True, ''

    def get(self, request):
        return self.post(request)

    def post(self, request):
        payment_id = self._extract_payment_id(request)
        if not payment_id:
            return JsonResponse({'ok': True, 'ignored': 'without_payment_id'})

        if not self._is_valid_signature(request, payment_id):
            return JsonResponse({'ok': False, 'error': 'invalid_signature'}, status=403)

        try:
            synced, reason = self._sync_by_payment_id(payment_id)
        except Exception:
            return JsonResponse({'ok': False, 'error': 'payment_sync_failed'}, status=400)

        if not synced:
            return JsonResponse({'ok': True, 'ignored': reason})

        return JsonResponse({'ok': True, 'payment_id': payment_id})


class LojaView(LoginRequiredMixin, View):
    template_name = 'loja.html'

    def _guard(self, request):
        if not _has_menu_permission(request, 'loja'):
            messages.error(request, 'Seu perfil não possui permissão para acessar Loja.')
            return redirect('accounts:painel')
        return None

    def _parse_valor(self, raw_value):
        raw = str(raw_value or '').strip()
        if not raw:
            return None
        normalized = raw.replace('R$', '').replace(' ', '')
        if ',' in normalized and '.' in normalized:
            normalized = normalized.replace('.', '').replace(',', '.')
        else:
            normalized = normalized.replace(',', '.')
        try:
            value = Decimal(normalized)
        except (InvalidOperation, ValueError):
            return None
        if value < 0:
            return None
        return value.quantize(Decimal('0.01'))

    def _context(self, form_data=None):
        produtos = (
            LojaProduto.objects
            .prefetch_related('variacoes')
            .order_by('-created_at')
        )
        rows = []
        for produto in produtos:
            variacoes = list(produto.variacoes.all())
            rows.append({
                'produto': produto,
                'variacoes': variacoes,
            })
        return {
            'produtos': rows,
            'form_data': form_data or {},
        }

    def get(self, request):
        guard = self._guard(request)
        if guard:
            return guard
        context = self._context()
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)

    def post(self, request):
        guard = self._guard(request)
        if guard:
            return guard

        titulo = str(request.POST.get('titulo') or '').strip()
        descricao = str(request.POST.get('descricao') or '').strip()
        foto = request.FILES.get('foto')
        var_names = request.POST.getlist('variacao_nome[]')
        var_values = request.POST.getlist('variacao_valor[]')
        var_stocks = request.POST.getlist('variacao_estoque[]')

        form_data = {
            'titulo': titulo,
            'descricao': descricao,
            'variacoes': [],
        }

        if not titulo:
            messages.error(request, 'Informe o título do produto.')
            context = self._context(form_data=form_data)
            context.update(_sidebar_context(request))
            return render(request, self.template_name, context)

        variacoes_parsed = []
        max_len = max(len(var_names), len(var_values), len(var_stocks), 1)
        for idx in range(max_len):
            nome = (var_names[idx] if idx < len(var_names) else '').strip()
            valor_raw = (var_values[idx] if idx < len(var_values) else '').strip()
            estoque_raw = (var_stocks[idx] if idx < len(var_stocks) else '').strip()
            form_data['variacoes'].append({
                'nome': nome,
                'valor': valor_raw,
                'estoque': estoque_raw,
            })

            if not nome and not valor_raw and not estoque_raw:
                continue
            if not nome:
                messages.error(request, f'Preencha o nome da variação na linha {idx + 1}.')
                context = self._context(form_data=form_data)
                context.update(_sidebar_context(request))
                return render(request, self.template_name, context)
            valor = self._parse_valor(valor_raw)
            if valor is None:
                messages.error(request, f'Informe um valor válido para a variação "{nome}".')
                context = self._context(form_data=form_data)
                context.update(_sidebar_context(request))
                return render(request, self.template_name, context)
            estoque = None
            if estoque_raw:
                if not re.fullmatch(r'-?\d+', estoque_raw):
                    messages.error(request, f'Estoque inválido para a variação "{nome}".')
                    context = self._context(form_data=form_data)
                    context.update(_sidebar_context(request))
                    return render(request, self.template_name, context)
                estoque = int(estoque_raw)
                if estoque < 0:
                    messages.error(request, f'Estoque não pode ser negativo para a variação "{nome}".')
                    context = self._context(form_data=form_data)
                    context.update(_sidebar_context(request))
                    return render(request, self.template_name, context)
            variacoes_parsed.append({
                'nome': nome,
                'valor': valor,
                'estoque': estoque,
            })

        if not variacoes_parsed:
            messages.error(request, 'Cadastre pelo menos uma variação com valor.')
            context = self._context(form_data=form_data)
            context.update(_sidebar_context(request))
            return render(request, self.template_name, context)

        with transaction.atomic():
            produto = LojaProduto.objects.create(
                titulo=titulo,
                descricao=descricao,
                foto=foto,
                created_by=request.user,
            )
            LojaProdutoVariacao.objects.bulk_create([
                LojaProdutoVariacao(
                    produto=produto,
                    nome=item['nome'],
                    valor=item['valor'],
                    estoque=item['estoque'],
                )
                for item in variacoes_parsed
            ])

        messages.success(request, f'Produto "{produto.titulo}" cadastrado com {len(variacoes_parsed)} variação(ões).')
        context = self._context()
        context.update(_sidebar_context(request))
        return render(request, self.template_name, context)


class UsuarioDetalheView(LoginRequiredMixin, View):
    template_name = 'usuario_detalhe.html'

    def get(self, request, pk):
        if not _has_menu_permission(request, 'usuarios'):
            messages.error(request, 'Seu perfil nÃ£o possui permissÃ£o para acessar usuÃ¡rios.')
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
    merge_lookup_limit = 200

    def _merge_candidates(self, target_user):
        return (
            User.objects
            .exclude(pk=target_user.pk)
            .order_by('username')
            .values_list('username', flat=True)[: self.merge_lookup_limit]
        )

    def _base_context(self, request, target_user, form):
        display = _user_display_data(target_user)
        context = {
            'form': form,
            'target_user': target_user,
            'nome_completo': display['nome_completo'],
            'foto_url': display['foto_url'],
            'merge_candidates': self._merge_candidates(target_user),
        }
        context.update(_sidebar_context(request))
        return context

    def _merge_users(self, target_user, source_user):
        if source_user.pk == target_user.pk:
            return False, 'Selecione outro usuï¿½rio para unificar.'

        source_responsavel = getattr(source_user, 'responsavel', None)
        source_diretoria = getattr(source_user, 'diretoria', None)
        target_responsavel = getattr(target_user, 'responsavel', None)
        target_diretoria = getattr(target_user, 'diretoria', None)

        if source_responsavel and target_responsavel:
            return False, 'Nï¿½o foi possï¿½vel unificar: ambos jï¿½ possuem cadastro de responsï¿½vel.'
        if source_diretoria and target_diretoria:
            return False, 'Nï¿½o foi possï¿½vel unificar: ambos jï¿½ possuem cadastro de diretoria.'

        with transaction.atomic():
            source_access = _ensure_user_access(source_user)
            target_access = _ensure_user_access(target_user)

            if source_responsavel:
                source_responsavel.user = target_user
                source_responsavel.save(update_fields=['user'])
            if source_diretoria:
                source_diretoria.user = target_user
                source_diretoria.save(update_fields=['user'])

            profiles = set(target_access.profiles or [])
            profiles.update(source_access.profiles or [])
            if target_access.role:
                profiles.add(target_access.role)
            if source_access.role:
                profiles.add(source_access.role)
            known = {choice[0] for choice in UserAccess.ROLE_CHOICES}
            merged_profiles = sorted(item for item in profiles if item in known)
            if not merged_profiles:
                merged_profiles = [UserAccess.ROLE_RESPONSAVEL]

            target_access.profiles = merged_profiles
            target_access.role = _primary_role_from_profiles(merged_profiles)
            target_access.menu_allow = sorted(set(_normalize_menu_keys(target_access.menu_allow)) | set(_normalize_menu_keys(source_access.menu_allow)))
            target_access.menu_deny = sorted(set(_normalize_menu_keys(target_access.menu_deny)) | set(_normalize_menu_keys(source_access.menu_deny)))
            target_access.save(update_fields=['role', 'profiles', 'menu_allow', 'menu_deny', 'updated_at'])

            target_group_ids = set(target_user.access_groups.values_list('id', flat=True))
            source_group_ids = set(source_user.access_groups.values_list('id', flat=True))
            merged_group_ids = sorted(target_group_ids | source_group_ids)
            if merged_group_ids:
                target_user.access_groups.set(merged_group_ids)
            source_user.access_groups.clear()

            source_user.is_active = False
            source_user.set_unusable_password()
            source_user.save(update_fields=['is_active', 'password'])

            source_access.profiles = []
            source_access.menu_allow = []
            source_access.menu_deny = []
            source_access.role = UserAccess.ROLE_RESPONSAVEL
            source_access.save(update_fields=['role', 'profiles', 'menu_allow', 'menu_deny', 'updated_at'])

        return True, ''

    def get(self, request, pk):
        if not _has_menu_permission(request, 'usuarios'):
            messages.error(request, 'Seu perfil nï¿½o possui permissï¿½o para editar usuï¿½rios.')
            return redirect('accounts:painel')
        target_user = get_object_or_404(User, pk=pk)
        access = _ensure_user_access(target_user)
        profiles = list(access.profiles or [])
        if not profiles and access.role:
            profiles = [access.role]
        form = UserAccessForm(initial={'profiles': profiles, 'is_active': target_user.is_active})
        return render(request, self.template_name, self._base_context(request, target_user, form))

    def post(self, request, pk):
        if not _has_menu_permission(request, 'usuarios'):
            messages.error(request, 'Seu perfil nï¿½o possui permissï¿½o para editar usuï¿½rios.')
            return redirect('accounts:painel')
        target_user = get_object_or_404(User, pk=pk)
        action = str(request.POST.get('action') or '').strip()

        if action == 'merge_user':
            source_username = str(request.POST.get('merge_username') or '').strip()
            if not source_username:
                messages.error(request, 'Informe o username que serï¿½ unificado.')
                return redirect('accounts:editar_usuario_permissoes', pk=target_user.pk)
            source_user = User.objects.filter(username=source_username).first()
            if not source_user:
                messages.error(request, 'Usuï¿½rio para unificaï¿½ï¿½o nï¿½o encontrado.')
                return redirect('accounts:editar_usuario_permissoes', pk=target_user.pk)
            ok, error_message = self._merge_users(target_user, source_user)
            if not ok:
                messages.error(request, error_message)
                return redirect('accounts:editar_usuario_permissoes', pk=target_user.pk)
            record_audit(
                action='Unificacao de usuarios',
                user=request.user,
                request=request,
                location='Usuarios',
                details=f'"{source_user.username}" incorporado em "{target_user.username}"',
            )
            messages.success(
                request,
                f'Unificaï¿½ï¿½o concluï¿½da: "{source_user.username}" foi incorporado em "{target_user.username}".',
            )
            return redirect('accounts:editar_usuario_permissoes', pk=target_user.pk)

        access = _ensure_user_access(target_user)
        form = UserAccessForm(request.POST)
        if form.is_valid():
            profiles = list(dict.fromkeys(form.cleaned_data['profiles']))
            access.profiles = profiles
            access.role = _primary_role_from_profiles(profiles)
            access.save(update_fields=['role', 'profiles', 'updated_at'])
            target_user.is_active = form.cleaned_data['is_active']
            target_user.save(update_fields=['is_active'])
            record_audit(
                action='Alteracao de permissoes',
                user=request.user,
                request=request,
                location='Usuarios',
                details=(
                    f'Usuario "{target_user.username}" | '
                    f'Perfis={",".join(profiles)} | '
                    f'Ativo={"sim" if target_user.is_active else "nao"}'
                ),
            )
            messages.success(request, 'Permissï¿½es atualizadas com sucesso.')
            return redirect('accounts:usuarios')
        return render(request, self.template_name, self._base_context(request, target_user, form))

