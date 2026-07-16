from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.shortcuts import get_object_or_404


class MeView(APIView):
    """Devuelve los datos del usuario autenticado (para el frontend)."""

    def get(self, request):
        u = request.user
        return Response({
            'id': u.id,
            'username': u.username,
            'nombre': u.get_full_name() or u.username,
            'email': u.email,
            'is_staff': u.is_staff,
        })

from .models import Contrato, AnexoTarifario, DetalleTarifa
from .serializers import (
    ContratoBusquedaSerializer,
    ContratoDetalleSerializer,
    DetalleTarifaSerializer,
    AnexoTarifarioSerializer,
)
from .services.excel_processor import ExcelTarifarioProcessor


class BuscadorContratoView(ListAPIView):
    serializer_class = ContratoBusquedaSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', None)
        if query:
            return Contrato.objects.select_related('administradora').filter(
                Q(administradora__nombre__icontains=query) |
                Q(administradora__nit__icontains=query) |
                Q(numero_contrato__icontains=query)
            ).filter(estado=Contrato.Estado.ACTIVO).order_by('administradora__nombre')
        return Contrato.objects.none()


class ContratoDetalleView(RetrieveAPIView):
    serializer_class = ContratoDetalleSerializer
    queryset = Contrato.objects.select_related('administradora').all()


class TarifasContratoView(ListAPIView):
    """Tarifas (DetalleTarifa) de todos los anexos de un contrato, con búsqueda local."""
    serializer_class = DetalleTarifaSerializer

    def get_queryset(self):
        contrato_id = self.kwargs['pk']
        qs = DetalleTarifa.objects.filter(
            anexo_origen__contrato_id=contrato_id
        ).order_by('codigo_cups')
        query = self.request.query_params.get('q')
        if query:
            qs = qs.filter(
                Q(codigo_cups__icontains=query) |
                Q(descripcion__icontains=query)
            )
        return qs


class AnexoUploadView(APIView):
    """Sube un Excel de tarifas, lo procesa y vuelca las filas a DetalleTarifa.

    El Excel se procesa en memoria: no se depende de que el archivo persista
    en disco (el disco de Railway es efímero). La fuente de verdad de los datos
    queda en la tabla DetalleTarifa (PostgreSQL).
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        contrato_id = request.data.get('contrato')
        nombre_anexo = request.data.get('nombre_anexo')
        archivo = request.FILES.get('archivo_excel')

        if not contrato_id or not archivo:
            return Response(
                {'error': 'Se requieren los campos "contrato" y "archivo_excel".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contrato = get_object_or_404(Contrato, pk=contrato_id)
        anexo = AnexoTarifario.objects.create(
            contrato=contrato,
            nombre_anexo=nombre_anexo or archivo.name,
            archivo_excel=archivo,
        )

        try:
            procesador = ExcelTarifarioProcessor(anexo, file_obj=archivo)
            filas = procesador.process()
        except Exception as exc:
            anexo.delete()
            return Response(
                {'error': f'No se pudo procesar el archivo: {exc}'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        data = AnexoTarifarioSerializer(anexo).data
        data['filas_procesadas'] = filas
        return Response(data, status=status.HTTP_201_CREATED)
