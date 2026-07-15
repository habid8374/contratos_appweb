from django.contrib import admin

from .models import Administradora, AlertaContrato, AnexoTarifario, Contrato, DetalleTarifa


@admin.register(Administradora)
class AdministradoraAdmin(admin.ModelAdmin):
    search_fields = ('nombre', 'nit')
    list_display = ('nombre', 'nit')


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    search_fields = ('numero_contrato', 'administradora__nombre')
    list_display = ('numero_contrato', 'administradora', 'modalidad', 'fecha_fin', 'estado')
    list_filter = ('modalidad', 'estado')


admin.site.register(AlertaContrato)
admin.site.register(AnexoTarifario)
admin.site.register(DetalleTarifa)
