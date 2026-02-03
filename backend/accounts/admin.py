from django.contrib import admin

from .models import Responsavel, Aventureiro


@admin.register(Responsavel)
class ResponsavelAdmin(admin.ModelAdmin):
    list_display = ('user', 'responsavel_nome', 'cidade', 'created_at')
    search_fields = ('user__username', 'pai_nome', 'responsavel_nome')


@admin.register(Aventureiro)
class AventureiroAdmin(admin.ModelAdmin):
    list_display = ('nome', 'responsavel', 'serie', 'created_at')
    search_fields = ('nome', 'responsavel__user__username')
