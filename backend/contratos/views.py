from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, ProtectedError
from django.shortcuts import get_object_or_404

from .models import Contrato, Administradora, AnexoTarifario, DetalleTarifa
from .serializers import (
    AdministradoraSerializer,
    ContratoBusquedaSerializer,
    ContratoDetalleSerializer,
    ContratoEscrituraSerializer,
    DetalleTarifaSerializer,
    AnexoTarifarioSerializer,
)
from .services.excel_processor import ExcelTarifarioProcessor


class MeView(APIView):
    """Datos del usuario autenticado (para el frontend)."""

    def get(self, request):
        u = request.user
        return Response({
            'id': u.id,
            'username': u.username,
            'nombre': u.get_full_name() or u.username,
            'email': u.email,
            'is_staff': u.is_staff,
        })


class AdministradoraViewSet(viewsets.ModelViewSet):
    queryset = Administradora.objects.all()
    serializer_class = AdministradoraSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get('q')
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(nit__icontains=q))
        return qs

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'error': 'No se puede eliminar: la administradora tiene contratos asociados.'},
                status=status.HTTP_409_CONFLICT,
            )


class ContratoViewSet(viewsets.ModelViewSet):
    queryset = Contrato.objects.select_related('administradora', 'alerta').all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ContratoEscrituraSerializer
        if self.action == 'list':
            return ContratoBusquedaSerializer
        return ContratoDetalleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        administradora = self.request.query_params.get('administradora')
        if administradora:
            qs = qs.filter(administradora_id=administradora)
        return qs

    @action(detail=False, methods=['get'], url_path='buscar')
    def buscar(self, request):
        query = request.query_params.get('q')
        if not query:
            return Response([])
        contratos = Contrato.objects.select_related('administradora').filter(
            Q(administradora__nombre__icontains=query) |
            Q(administradora__nit__icontains=query) |
            Q(numero_contrato__icontains=query)
        ).filter(estado=Contrato.Estado.ACTIVO).order_by('administradora__nombre')
        return Response(ContratoBusquedaSerializer(contratos, many=True).data)

    @action(detail=True, methods=['get'], url_path='tarifas')
    def tarifas(self, request, pk=None):
        qs = DetalleTarifa.objects.filter(anexo_origen__contrato_id=pk).order_by('codigo_cups')
        query = request.query_params.get('q')
        if query:
            qs = qs.filter(Q(codigo_cups__icontains=query) | Q(descripcion__icontains=query))
        return Response(DetalleTarifaSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='anexos')
    def anexos(self, request, pk=None):
        anexos = AnexoTarifario.objects.filter(contrato_id=pk).order_by('-fecha_carga')
        return Response(AnexoTarifarioSerializer(anexos, many=True).data)

    @action(detail=False, methods=['get'], url_path='alertas')
    def alertas(self, request):
        """Contratos activos ordenados por vencimiento, marcando los que ya
        entraron en su ventana de alerta configurada."""
        from datetime import date
        hoy = date.today()
        contratos = (
            Contrato.objects.select_related('administradora', 'alerta')
            .filter(estado=Contrato.Estado.ACTIVO)
            .order_by('fecha_fin')
        )
        data = []
        for c in contratos:
            dias = (c.fecha_fin - hoy).days if c.fecha_fin else None
            alerta = getattr(c, 'alerta', None)
            dias_previos = alerta.dias_previos if (alerta and alerta.activa) else None
            en_alerta = (
                dias is not None and dias_previos is not None and dias <= dias_previos
            )
            data.append({
                'id': c.id,
                'numero_contrato': c.numero_contrato,
                'administradora': c.administradora.nombre,
                'fecha_inicio': c.fecha_inicio,
                'fecha_fin': c.fecha_fin,
                'dias_para_vencer': dias,
                'dias_previos': dias_previos,
                'alerta_activa': bool(alerta and alerta.activa),
                'en_alerta': en_alerta,
                'vencido': dias is not None and dias < 0,
            })
        return Response(data)


class AnexoUploadView(APIView):
    """Sube un Excel de tarifas, lo procesa (en memoria) y vuelca a DetalleTarifa."""
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
            filas, resumen = ExcelTarifarioProcessor(anexo, file_obj=archivo).process()
        except Exception as exc:
            anexo.delete()
            return Response(
                {'error': f'No se pudo procesar el archivo: {exc}'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        data = AnexoTarifarioSerializer(anexo).data
        data['filas_procesadas'] = filas
        data['resumen_hojas'] = resumen
        return Response(data, status=status.HTTP_201_CREATED)
