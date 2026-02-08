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
