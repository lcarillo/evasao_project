from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # Corrigido para views.dashboard
    path('signup/', views.signup, name='signup'),
    path('login/', views.custom_login, name='login'),
path('logout/', views.custom_logout, name='logout'),
]