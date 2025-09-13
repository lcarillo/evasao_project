from django.db import models
from django.contrib.auth.models import User


class Municipio(models.Model):
    codigo = models.IntegerField(unique=True)
    nome = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    regiao = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.nome} - {self.uf}"


class DadosEvasao(models.Model):
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    ano = models.IntegerField()
    total = models.FloatField()
    serie_1 = models.FloatField(null=True, blank=True)
    serie_2 = models.FloatField(null=True, blank=True)
    serie_3 = models.FloatField(null=True, blank=True)
    serie_4 = models.FloatField(null=True, blank=True)
    nao_seriado = models.FloatField(null=True, blank=True)

    class Meta:
        unique_together = ('municipio', 'ano')

    def __str__(self):
        return f"{self.municipio.nome} - {self.ano}: {self.total}%"


class PrevisaoEvasao(models.Model):
    municipio = models.ForeignKey(Municipio, on_delete=models.CASCADE)
    ano = models.IntegerField()
    previsao = models.FloatField()
    limite_inferior = models.FloatField()
    limite_superior = models.FloatField()

    class Meta:
        unique_together = ('municipio', 'ano')

    def __str__(self):
        return f"{self.municipio.nome} - {self.ano}: {self.previsao}%"


class MetricasModelo(models.Model):
    municipio = models.OneToOneField(Municipio, on_delete=models.CASCADE)
    mae = models.FloatField()
    rmse = models.FloatField()
    mape = models.FloatField()
    data_calculo = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Métricas para {self.municipio.nome}"