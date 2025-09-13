from django.contrib import admin
from .models import Municipio, DadosEvasao, PrevisaoEvasao, MetricasModelo

@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'uf', 'regiao')
    search_fields = ('nome', 'codigo')

@admin.register(DadosEvasao)
class DadosEvasaoAdmin(admin.ModelAdmin):
    list_display = ('municipio', 'ano', 'total')
    list_filter = ('ano', 'municipio__uf')
    search_fields = ('municipio__nome',)

@admin.register(PrevisaoEvasao)
class PrevisaoEvasaoAdmin(admin.ModelAdmin):
    list_display = ('municipio', 'ano', 'previsao')
    list_filter = ('ano', 'municipio__uf')
    search_fields = ('municipio__nome',)

@admin.register(MetricasModelo)
class MetricasModeloAdmin(admin.ModelAdmin):
    list_display = ('municipio', 'mae', 'rmse', 'mape', 'data_calculo')
    search_fields = ('municipio__nome',)