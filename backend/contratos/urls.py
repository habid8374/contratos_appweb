
from django.urls import path
from .views import (
    BuscadorContratoView,
    ContratoDetalleView,
    TarifasContratoView,
    AnexoUploadView,
    MeView,
)

urlpatterns = [
    path('auth/me/', MeView.as_view(), name='me'),
    path('contratos/buscar/', BuscadorContratoView.as_view(), name='buscar-contratos'),
    path('contratos/<int:pk>/', ContratoDetalleView.as_view(), name='detalle-contrato'),
    path('contratos/<int:pk>/tarifas/', TarifasContratoView.as_view(), name='tarifas-contrato'),
    path('anexos/', AnexoUploadView.as_view(), name='cargar-anexo'),
]
