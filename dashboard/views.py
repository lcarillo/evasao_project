from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .forms import SignUpForm
from .models import Municipio, DadosEvasao, PrevisaoEvasao, MetricasModelo
from django.core.paginator import Paginator
from django.http import HttpRequest
from django.db.models import Q


def home(request):
    return render(request, 'home.html')


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})


def custom_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuário ou senha inválidos.')
    return render(request, 'login.html')


@login_required
def dashboard(request: HttpRequest):
    # Número de itens por página
    ITEMS_PER_PAGE = 10000

    # Obter parâmetros de filtro
    municipio_filter = request.GET.get('municipio', '')
    ano_filter = request.GET.get('ano', '')
    sort_by = request.GET.get('sort', '')
    sort_order = request.GET.get('order', 'asc')

    # Buscar dados reais do banco
    dados_brutos_query = DadosEvasao.objects.select_related('municipio').order_by('-ano')
    previsoes_query = PrevisaoEvasao.objects.select_related('municipio').all()
    metricas_query = MetricasModelo.objects.select_related('municipio').all()

    # Aplicar filtros
    if municipio_filter:
        dados_brutos_query = dados_brutos_query.filter(municipio__nome__icontains=municipio_filter)
        previsoes_query = previsoes_query.filter(municipio__nome__icontains=municipio_filter)
        metricas_query = metricas_query.filter(municipio__nome__icontains=municipio_filter)

    if ano_filter:
        try:
            ano = int(ano_filter)
            dados_brutos_query = dados_brutos_query.filter(ano=ano)
            previsoes_query = previsoes_query.filter(ano=ano)
        except ValueError:
            pass

    # Aplicar ordenação
    if sort_by:
        if sort_order == 'desc':
            sort_by = f'-{sort_by}'

        if sort_by in ['municipio', '-municipio', 'ano', '-ano', 'total', '-total']:
            dados_brutos_query = dados_brutos_query.order_by(sort_by)

        if sort_by in ['municipio', '-municipio', 'ano', '-ano', 'previsao', '-previsao']:
            previsoes_query = previsoes_query.order_by(sort_by)

        if sort_by in ['municipio', '-municipio', 'mae', '-mae', 'rmse', '-rmse']:
            metricas_query = metricas_query.order_by(sort_by)

    # Paginação
    page_number = request.GET.get('page', 1)
    paginator_dados = Paginator(dados_brutos_query, ITEMS_PER_PAGE)
    paginator_previsoes = Paginator(previsoes_query, ITEMS_PER_PAGE)

    dados_brutos_page = paginator_dados.get_page(page_number)
    previsoes_page = paginator_previsoes.get_page(page_number)

    context = {
        'dados_brutos': [{
            'municipio': d.municipio.nome,
            'ano': d.ano,
            'total': d.total
        } for d in dados_brutos_page],
        'previsoes': [{
            'municipio': p.municipio.nome,
            'ano': p.ano,
            'previsao': p.previsao,
            'limite_inferior': p.limite_inferior,
            'limite_superior': p.limite_superior
        } for p in previsoes_page],
        'metricas': [{
            'municipio': m.municipio.nome,
            'mae': m.mae,
            'rmse': m.rmse
        } for m in metricas_query],
        'total_municipios': Municipio.objects.count(),
        'usuario': request.user,
        'periodo_treino': '2018-2023',
        'periodo_validacao': '2024',
        'municipio_filter': municipio_filter,
        'ano_filter': ano_filter,
        'sort_by': sort_by,
        'sort_order': sort_order
    }

    return render(request, 'dashboard.html', context)


def custom_logout(request):
    logout(request)
    return redirect('home')