
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdministradoraViewSet,
    ContratoViewSet,
    AnexoUploadView,
    MeView,
)

router = DefaultRouter()
router.register('administradoras', AdministradoraViewSet, basename='administradora')
router.register('contratos', ContratoViewSet, basename='contrato')

urlpatterns = [
    path('auth/me/', MeView.as_view(), name='me'),
    path('anexos/', AnexoUploadView.as_view(), name='cargar-anexo'),
    path('', include(router.urls)),
]
