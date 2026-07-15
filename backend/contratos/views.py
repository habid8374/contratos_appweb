
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.db.models import Q
from .models import Contrato
from .serializers import ContratoBusquedaSerializer, ContratoDetalleSerializer


class BuscadorContratoView(ListAPIView):
    serializer_class = ContratoBusquedaSerializer
    # permission_classes = [IsAuthenticated] # Descomentar cuando JWT esté listo

    def get_queryset(self):
        query = self.request.query_params.get('q', None)
        if query:
            return Contrato.objects.select_related('administradora').filter(
                Q(administradora__nombre__icontains=query) |
                Q(numero_contrato__icontains=query)
            ).filter(estado=Contrato.Estado.ACTIVO).order_by('administradora__nombre')
        return Contrato.objects.none()


class ContratoDetalleView(RetrieveAPIView):
    serializer_class = ContratoDetalleSerializer
    queryset = Contrato.objects.select_related('administradora').all()
