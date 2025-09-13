import pandas as pd
import numpy as np
from prophet import Prophet
from .utils import calcular_metricas
import logging

# Configurar logging
logging.getLogger('prophet').setLevel(logging.WARNING)
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)


class EvasaoProphetPipeline:
    def __init__(self, dados_historicos):
        """
        Inicializa o pipeline de previsão com Prophet

        Args:
            dados_historicos (DataFrame): DataFrame com dados históricos de evasão
        """
        self.dados_historicos = dados_historicos
        self.modelos = {}
        self.previsoes = {}
        self.metricas = {}

    def preparar_dados(self, municipio_codigo):
        """
        Prepara os dados no formato exigido pelo Prophet para um município específico

        Args:
            municipio_codigo (int): Código do município

        Returns:
            DataFrame: Dados no formato Prophet (ds, y)
        """
        # Filtrar dados para o município específico
        dados_municipio = self.dados_historicos[
            self.dados_historicos['Código do Município'] == municipio_codigo
            ].copy()

        if dados_municipio.empty:
            raise ValueError(f"Nenhum dado encontrado para o município com código {municipio_codigo}")

        # Ordenar por ano
        dados_municipio = dados_municipio.sort_values('Ano')

        # Converter para formato Prophet (ds = data, y = valor)
        dados_prophet = pd.DataFrame({
            'ds': pd.to_datetime(dados_municipio['Ano'].astype(str) + '-12-31'),
            'y': dados_municipio['Total']
        })

        return dados_prophet

    def treinar_modelo(self, dados_treino):
        """
        Treina o modelo Prophet com os dados fornecidos

        Args:
            dados_treino (DataFrame): Dados de treino no formato Prophet

        Returns:
            Prophet: Modelo treinado
        """
        # Configurar e treinar o modelo
        modelo = Prophet(
            yearly_seasonality=True,
            seasonality_mode='multiplicative',
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10
        )

        modelo.fit(dados_treino)
        return modelo

    def fazer_previsao(self, modelo, periodos=2):
        """
        Faz previsões para os próximos períodos

        Args:
            modelo (Prophet): Modelo treinado
            periodos (int): Número de períodos futuros para prever

        Returns:
            DataFrame: Previsões com intervalos de confiança
        """
        # Criar dataframe futuro
        futuro = modelo.make_future_dataframe(periods=periodos, freq='Y', include_history=False)

        # Fazer previsão
        previsao = modelo.predict(futuro)

        return previsao[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]

    def executar_pipeline(self, municipio_codigo):
        """
        Executa o pipeline completo para um município

        Args:
            municipio_codigo (int): Código do município

        Returns:
            dict: Dicionário com resultados e métricas
        """
        try:
            # Preparar dados
            dados_completos = self.preparar_dados(municipio_codigo)

            # Separar treino (2018-2023) e validação (2024)
            dados_treino = dados_completos[dados_completos['ds'] < '2024-01-01']
            dados_validacao = dados_completos[dados_completos['ds'] >= '2024-01-01']

            if dados_treino.empty:
                raise ValueError("Dados de treino insuficientes (2018-2023)")

            # Treinar modelo
            modelo = self.treinar_modelo(dados_treino)
            self.modelos[municipio_codigo] = modelo

            # Fazer previsão para validação (2024) e futuro (2025-2026)
            previsao_validacao = modelo.predict(
                modelo.make_future_dataframe(periods=1, freq='Y', include_history=False)
            )

            previsao_futuro = self.fazer_previsao(modelo, periodos=2)

            # Calcular métricas se houver dados de validação
            if not dados_validacao.empty:
                y_true = dados_validacao['y'].values
                y_pred = previsao_validacao['yhat'].values

                self.metricas[municipio_codigo] = calcular_metricas(y_true, y_pred)

            # Preparar resultados
            resultados = {
                'historico': dados_completos,
                'previsao_2024': previsao_validacao[['ds', 'yhat', 'yhat_lower', 'yhat_upper']],
                'previsao_2025_2026': previsao_futuro,
                'metricas': self.metricas.get(municipio_codigo, {})
            }

            return resultados

        except Exception as e:
            print(f"Erro ao processar município {municipio_codigo}: {str(e)}")
            return None

    def processar_todos_municipios(self):
        """
        Processa todos os municípios presentes nos dados históricos

        Returns:
            dict: Resultados para todos os municípios
        """
        resultados_gerais = {}
        municipios = self.dados_historicos['Código do Município'].unique()

        for municipio_codigo in municipios:
            resultados = self.executar_pipeline(municipio_codigo)
            if resultados:
                resultados_gerais[municipio_codigo] = resultados

        return resultados_gerais


# Função principal para executar o pipeline
def executar_pipeline_prophet(caminho_arquivo):
    """
    Função principal para executar o pipeline completo

    Args:
        caminho_arquivo (str): Caminho para o arquivo Excel com os dados

    Returns:
        dict: Resultados do pipeline para todos os municípios
    """
    # Carregar dados
    dados = pd.read_excel(caminho_arquivo)

    # Filtrar apenas para SP e coluna Total
    dados_sp = dados[dados['UF'] == 'SP'].copy()

    # Criar e executar pipeline
    pipeline = EvasaoProphetPipeline(dados_sp)
    resultados = pipeline.processar_todos_municipios()

    return resultados