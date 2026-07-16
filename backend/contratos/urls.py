
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdministradoraViewSet,
    ContratoViewSet,
    NotaTecnicaViewSet,
    AnexoUploadView,
    ConsumoUploadView,
    MeView,
)

router = DefaultRouter()
router.register('administradoras', AdministradoraViewSet, basename='administradora')
router.register('contratos', ContratoViewSet, basename='contrato')
router.register('notas-tecnicas', NotaTecnicaViewSet, basename='nota-tecnica')

urlpatterns = [
    path('auth/me/', MeView.as_view(), name='me'),
    path('anexos/', AnexoUploadView.as_view(), name='cargar-anexo'),
    path('consumo/', ConsumoUploadView.as_view(), name='cargar-consumo'),
    path('', include(router.urls)),
]
