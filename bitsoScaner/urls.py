from django.urls import path

from . import views

urlpatterns = [
    path('<int:acc>/<str:coin>/', views.CoinDashboard.as_view(), name='coindashboard'),
]