from django.contrib import admin

from .models import (
    Responsavel,
    Aventureiro,
    Diretoria,
    UserAccess,
    WhatsAppPreference,
    WhatsAppQueue,
    WhatsAppTemplate,
    EventoPresenca,
    AuditLog,
    MensalidadeAventureiro,
    PagamentoMensalidade,
    FinanceiroComprovante,
    AventureiroCashbackLancamento,
    LojaPedido,
)


@admin.register(Responsavel)
class ResponsavelAdmin(admin.ModelAdmin):
    list_display = ('user', 'responsavel_nome', 'cidade', 'created_at')
    search_fields = ('user__username', 'pai_nome', 'responsavel_nome')


@admin.register(Aventureiro)
class AventureiroAdmin(admin.ModelAdmin):
    list_display = ('nome', 'responsavel', 'serie', 'created_at')
    search_fields = ('nome', 'responsavel__user__username')


@admin.register(Diretoria)
class DiretoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'user', 'cidade', 'created_at')
    search_fields = ('nome', 'user__username', 'cpf')


@admin.register(UserAccess)
class UserAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'profiles_preview', 'updated_at')
    list_filter = ('role',)
    search_fields = ('user__username',)
    actions = ('definir_como_diretor', 'definir_como_diretoria', 'definir_como_responsavel')

    @admin.action(description='Definir perfil como Diretor')
    def definir_como_diretor(self, request, queryset):
        for access in queryset:
            access.add_profile(UserAccess.ROLE_DIRETOR)
            access.role = UserAccess.ROLE_DIRETOR
            access.save(update_fields=['role', 'profiles', 'updated_at'])

    @admin.action(description='Definir perfil como Diretoria')
    def definir_como_diretoria(self, request, queryset):
        for access in queryset:
            access.add_profile(UserAccess.ROLE_DIRETORIA)
            access.role = UserAccess.ROLE_DIRETORIA
            access.save(update_fields=['role', 'profiles', 'updated_at'])

    @admin.action(description='Definir perfil como Responsavel')
    def definir_como_responsavel(self, request, queryset):
        for access in queryset:
            access.add_profile(UserAccess.ROLE_RESPONSAVEL)
            access.role = UserAccess.ROLE_RESPONSAVEL
            access.save(update_fields=['role', 'profiles', 'updated_at'])

    def profiles_preview(self, obj):
        return ', '.join(obj.get_profiles_display())

    profiles_preview.short_description = 'perfis'


@admin.register(WhatsAppPreference)
class WhatsAppPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'notify_cadastro', 'notify_diretoria', 'notify_confirmacao', 'notify_financeiro', 'notify_geral', 'updated_at')
    search_fields = ('user__username', 'phone_number')
    list_filter = ('notify_cadastro', 'notify_diretoria', 'notify_confirmacao', 'notify_financeiro', 'notify_geral')


@admin.register(WhatsAppQueue)
class WhatsAppQueueAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'notification_type', 'status', 'attempts', 'created_at', 'sent_at')
    search_fields = ('phone_number', 'user__username', 'provider_message_id')
    list_filter = ('status', 'notification_type')


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = ('notification_type', 'updated_at')
    search_fields = ('notification_type',)


@admin.register(EventoPresenca)
class EventoPresencaAdmin(admin.ModelAdmin):
    list_display = ('evento', 'aventureiro', 'presente', 'updated_by', 'updated_at')
    search_fields = ('evento__name', 'aventureiro__nome', 'aventureiro__responsavel__user__username')
    list_filter = ('presente', 'evento')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'username', 'profile', 'location', 'action')
    search_fields = ('username', 'location', 'action', 'details', 'path', 'ip_address')
    list_filter = ('method', 'created_at')


@admin.register(MensalidadeAventureiro)
class MensalidadeAventureiroAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'aventureiro',
        'competencia',
        'tipo',
        'valor',
        'status',
        'created_at',
    )
    search_fields = (
        'aventureiro__nome',
        'aventureiro__responsavel__user__username',
    )
    list_filter = ('status', 'tipo', 'ano_referencia', 'mes_referencia')
    autocomplete_fields = ('aventureiro',)
    readonly_fields = ('created_at', 'updated_at')

    def competencia(self, obj):
        return f'{obj.mes_referencia:02d}/{obj.ano_referencia}'

    competencia.short_description = 'competencia'


@admin.register(PagamentoMensalidade)
class PagamentoMensalidadeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'responsavel',
        'valor_total',
        'status',
        'paid_at',
        'mp_payment_id',
        'created_at',
    )
    search_fields = (
        'responsavel__user__username',
        'responsavel__responsavel_nome',
        'mp_payment_id',
        'mp_external_reference',
    )
    list_filter = ('status', 'paid_at', 'created_at')
    filter_horizontal = ('mensalidades',)
    autocomplete_fields = ('responsavel', 'created_by')
    readonly_fields = ('created_at', 'updated_at')

    def _reabrir_mensalidades(self, pagamento):
        pagamento.mensalidades.filter(
            status=MensalidadeAventureiro.STATUS_PAGA
        ).update(status=MensalidadeAventureiro.STATUS_PENDENTE)

    def delete_model(self, request, obj):
        self._reabrir_mensalidades(obj)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        for pagamento in queryset.prefetch_related('mensalidades'):
            self._reabrir_mensalidades(pagamento)
        super().delete_queryset(request, queryset)


@admin.register(FinanceiroComprovante)
class FinanceiroComprovanteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'valor', 'created_by', 'created_at')
    search_fields = ('nome', 'created_by__username')
    list_filter = ('created_at',)
    autocomplete_fields = ('created_by',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AventureiroCashbackLancamento)
class AventureiroCashbackLancamentoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'aventureiro',
        'tipo',
        'valor',
        'saldo_apos',
        'evento_inscricao',
        'loja_pedido',
        'created_at',
    )
    search_fields = (
        'aventureiro__nome',
        'aventureiro__responsavel__user__username',
        'descricao',
    )
    list_filter = ('tipo', 'created_at')
    autocomplete_fields = ('aventureiro', 'loja_pedido', 'created_by')
    raw_id_fields = ('evento_inscricao',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LojaPedido)
class LojaPedidoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'responsavel',
        'evento',
        'evento_inscricao',
        'valor_total',
        'status',
        'paid_at',
        'created_at',
    )
    search_fields = (
        'responsavel__user__username',
        'mp_payment_id',
        'mp_external_reference',
    )
    list_filter = ('status', 'paid_at', 'created_at', 'evento')
    autocomplete_fields = ('responsavel', 'cashback_aventureiro', 'created_by')
    raw_id_fields = ('evento', 'evento_inscricao')
    readonly_fields = ('created_at', 'updated_at')
