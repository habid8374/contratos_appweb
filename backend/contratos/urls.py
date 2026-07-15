
from django.urls import path
from .views import BuscadorContratoView, ContratoDetalleView

urlpatterns = [
    path('contratos/buscar/', BuscadorContratoView.as_view(), name='buscar-contratos'),
    path('contratos/<int:pk>/', ContratoDetalleView.as_view(), name='detalle-contrato'),
]
