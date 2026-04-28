from django.urls import path
from . import views

urlpatterns = [
    path('bank-accounts/', views.bank_accounts, name='bank-accounts'),
    path('', views.payouts, name='payouts'),
]
