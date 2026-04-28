from django.urls import path
from . import views

urlpatterns = [
    path('', views.ledger_list, name='ledger-list'),
]
