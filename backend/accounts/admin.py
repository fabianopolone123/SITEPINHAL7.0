from django.contrib import admin

from .models import Responsavel, Aventureiro, Diretoria, UserAccess


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
    list_display = ('user', 'role', 'updated_at')
    list_filter = ('role',)
    search_fields = ('user__username',)
    actions = ('definir_como_diretor', 'definir_como_diretoria', 'definir_como_responsavel')

    @admin.action(description='Definir perfil como Diretor')
    def definir_como_diretor(self, request, queryset):
        queryset.update(role=UserAccess.ROLE_DIRETOR)

    @admin.action(description='Definir perfil como Diretoria')
    def definir_como_diretoria(self, request, queryset):
        queryset.update(role=UserAccess.ROLE_DIRETORIA)

    @admin.action(description='Definir perfil como Responsavel')
    def definir_como_responsavel(self, request, queryset):
        queryset.update(role=UserAccess.ROLE_RESPONSAVEL)
