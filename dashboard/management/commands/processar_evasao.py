from django.core.management.base import BaseCommand
from dashboard.data_processor import processar_dados_evasao


class Command(BaseCommand):
    help = 'Processa os dados de evasão escolar e gera previsões'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando processamento de dados de evasão...')
        processar_dados_evasao()
        self.stdout.write(
            self.style.SUCCESS('Processamento concluído com sucesso!')
        )