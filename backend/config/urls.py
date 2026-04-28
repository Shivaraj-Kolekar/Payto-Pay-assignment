from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
  #  path('', views.db_version, name='db_version'),

    # Auth
    path('api/v1/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # App routes
    path('api/v1/merchants/', include('apps.merchants.urls')),
    path('api/v1/ledger/', include('apps.ledger.urls')),
    path('api/v1/payouts/', include('apps.payouts.urls')),
]
