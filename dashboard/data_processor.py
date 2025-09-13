import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error
from django.db import transaction
import logging

# Configurar logging
logger = logging.getLogger(__name__)


def calcular_metricas(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    return {'mae': mae, 'rmse': rmse, 'mape': mape}


@transaction.atomic
def processar_dados_evasao():
    # Importar modelos aqui para evitar circular imports
    from .models import Municipio, DadosEvasao, PrevisaoEvasao, MetricasModelo

    # Carregar a base de dados
    caminho_arquivo = 'base_sp_abandono.xlsx'

    try:
        dados = pd.read_excel(caminho_arquivo)
        print(f"✅ Arquivo carregado com sucesso!")
        print(f"📊 Colunas encontradas: {dados.columns.tolist()}")

    except Exception as e:
        logger.error(f"❌ Erro ao carregar arquivo: {str(e)}")
        return

    # Converter colunas numéricas que podem ter '--' para NaN
    colunas_numericas = ['Total', '1ªsérie', '2ªsérie', '3ªsérie', '4ªsérie', 'Não-Seriado']

    for coluna in colunas_numericas:
        if coluna in dados.columns:
            if dados[coluna].dtype == 'object':
                # Substituir '--' por NaN e converter para float
                dados[coluna] = dados[coluna].replace('--', np.nan)
                dados[coluna] = pd.to_numeric(dados[coluna], errors='coerce')
                print(f"✅ Coluna {coluna} convertida para numérico")

    # Remover linhas com valores NaN na coluna Total
    dados = dados.dropna(subset=['Total'])
    print(f"📋 Dados após remover NaN: {len(dados)} registros")

    # Filtrar apenas para SP e dados totais
    try:
        dados_sp = dados[(dados['UF'] == 'SP')].copy()

        # Verificar se as colunas de filtro existem
        if 'Localização' in dados_sp.columns:
            dados_sp = dados_sp[dados_sp['Localização'] == 'Total']
        if 'Dependência Administrativa' in dados_sp.columns:
            dados_sp = dados_sp[dados_sp['Dependência Administrativa'] == 'Total']

        print(f"✅ Dados filtrados: {len(dados_sp)} registros")

    except Exception as e:
        logger.error(f"Erro ao filtrar dados: {str(e)}")
        return

    # Processar cada município
    municipios_processados = 0
    for codigo in dados_sp['Código do Município'].unique():
        try:
            # Filtrar dados do município
            dados_municipio = dados_sp[dados_sp['Código do Município'] == codigo].copy()

            if len(dados_municipio) == 0:
                continue

            # Obter informações do município
            info_municipio = dados_municipio.iloc[0]
            nome_municipio = info_municipio['Nome do Município']
            regiao = info_municipio['Região']

            print(f"\n📊 Processando {nome_municipio} ({codigo}) - {len(dados_municipio)} registros")
            print(f"📅 Anos disponíveis: {sorted(dados_municipio['Ano'].tolist())}")

            # Criar ou atualizar registro do município
            municipio, created = Municipio.objects.get_or_create(
                codigo=codigo,
                defaults={
                    'nome': nome_municipio,
                    'uf': 'SP',
                    'regiao': regiao
                }
            )

            # Preparar dados para o Prophet
            dados_prophet = pd.DataFrame({
                'ds': pd.to_datetime(dados_municipio['Ano'].astype(str) + '-12-31'),
                'y': dados_municipio['Total']
            })

            # Verificar se temos dados de 2024, se não, criar com base no último ano
            ultimo_ano = dados_prophet['ds'].max().year
            if ultimo_ano < 2024:
                # Encontrar o valor do último ano disponível
                ultimo_valor = dados_prophet[dados_prophet['ds'].dt.year == ultimo_ano]['y'].values[0]

                # Adicionar 2024 com o valor do último ano (como estimativa conservadora)
                dados_2024 = pd.DataFrame({
                    'ds': [pd.to_datetime('2024-12-31')],
                    'y': [ultimo_valor]
                })
                dados_prophet = pd.concat([dados_prophet, dados_2024], ignore_index=True)
                print(f"⚠️  Dados de 2024 não encontrados. Usando valor de {ultimo_ano}: {ultimo_valor}%")

            # Separar treino (até 2023) e validação (2024)
            dados_treino = dados_prophet[dados_prophet['ds'] < '2024-01-01']
            dados_validacao = dados_prophet[dados_prophet['ds'] >= '2024-01-01']

            if len(dados_treino) < 3:  # Mínimo de dados para treino
                print(f"❌ Dados insuficientes para treino: {len(dados_treino)} registros")
                continue

            print(f"🔧 Treino: {len(dados_treino)} anos, Validação: {len(dados_validacao)} anos")

            # Treinar modelo Prophet
            modelo = Prophet(
                yearly_seasonality=True,
                seasonality_mode='multiplicative',
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10
            )

            modelo.fit(dados_treino)

            # Fazer previsão para 2025 e 2026 - CORREÇÃO AQUI
            # Criar datas futuras manualmente para garantir 2025 e 2026
            futuro = pd.DataFrame({
                'ds': pd.to_datetime(['2025-12-31', '2026-12-31'])
            })

            print(f"📅 Fazendo previsão para anos: {[d.year for d in futuro['ds']]}")

            previsao = modelo.predict(futuro)

            # Debug: verificar o que foi previsto
            print(f"🔍 Previsões geradas:")
            for _, row in previsao.iterrows():
                print(f"   {row['ds'].year}: {row['yhat']:.2f}% ({row['yhat_lower']:.2f}% - {row['yhat_upper']:.2f}%)")

            # Calcular métricas usando 2024 como validação
            metricas = None
            if not dados_validacao.empty:
                # Fazer previsão para 2024 para validação
                futuro_validacao = pd.DataFrame({
                    'ds': pd.to_datetime(['2024-12-31'])
                })
                previsao_validacao = modelo.predict(futuro_validacao)

                if not previsao_validacao.empty:
                    y_true = dados_validacao['y'].values
                    y_pred = previsao_validacao['yhat'].values

                    # Verificar se os valores são válidos para cálculo
                    if len(y_true) > 0 and len(y_pred) > 0 and not np.isnan(y_true).any() and not np.isnan(
                            y_pred).any():
                        try:
                            metricas = calcular_metricas(y_true, y_pred)
                            print(f"📈 Métricas para {nome_municipio}:")
                            print(
                                f"   MAE={metricas['mae']:.3f}% (Erro médio de {metricas['mae']:.3f} pontos percentuais)")
                            print(f"   RMSE={metricas['rmse']:.3f}%")
                            print(f"   MAPE={metricas['mape']:.1f}%")

                        except Exception as e:
                            print(f"❌ Erro ao calcular métricas: {str(e)}")
                    else:
                        print(f"⚠️  Valores inválidos para cálculo de métricas")
            else:
                print(f"⚠️  Sem dados de validação para cálculo de métricas")

            # Salvar dados históricos
            for _, row in dados_municipio.iterrows():
                DadosEvasao.objects.update_or_create(
                    municipio=municipio,
                    ano=row['Ano'],
                    defaults={
                        'total': row['Total'],
                        'serie_1': row.get('1ªsérie', None),
                        'serie_2': row.get('2ªsérie', None),
                        'serie_3': row.get('3ªsérie', None),
                        'serie_4': row.get('4ªsérie', None),
                        'nao_seriado': row.get('Não-Seriado', None)
                    }
                )

            # Salvar previsões para 2025 e 2026
            for _, row in previsao.iterrows():
                ano = row['ds'].year
                PrevisaoEvasao.objects.update_or_create(
                    municipio=municipio,
                    ano=ano,
                    defaults={
                        'previsao': row['yhat'],
                        'limite_inferior': row['yhat_lower'],
                        'limite_superior': row['yhat_upper']
                    }
                )

            # Salvar métricas
            if metricas:
                MetricasModelo.objects.update_or_create(
                    municipio=municipio,
                    defaults={
                        'mae': metricas['mae'],
                        'rmse': metricas['rmse'],
                        'mape': metricas['mape']
                    }
                )

            municipios_processados += 1
            print(f"✅ Município {nome_municipio} processado com sucesso")

        except Exception as e:
            logger.error(f"❌ Erro ao processar município {codigo}: {str(e)}")
            print(f"❌ Erro ao processar município {codigo}: {str(e)}")

    print(f"\n🎉 Processamento concluído! {municipios_processados} municípios processados.")