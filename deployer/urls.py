from django.urls import path
from .views import (
    HomeView,
    PrepareDeploymentView,
    VerifyContractView,
    HealthCheckView
)


app_name = 'deployer'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('api/prepare-deployment/', PrepareDeploymentView.as_view(), name='prepare-deployment'),
    path('api/verify-contract/', VerifyContractView.as_view(), name='verify-contract'),
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
]