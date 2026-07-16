from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q, Sum, ProtectedError
from django.shortcuts import get_object_or_404

from .models import (
    Contrato, Administradora, AnexoTarifario, DetalleTarifa,
    NotaTecnica, RegistroConsumo,
)
from .serializers import (
    AdministradoraSerializer,
    ContratoBusquedaSerializer,
    ContratoDetalleSerializer,
    ContratoEscrituraSerializer,
    DetalleTarifaSerializer,
    AnexoTarifarioSerializer,
    NotaTecnicaSerializer,
    LineaNotaTecnicaSerializer,
)
from .services.excel_processor import ExcelTarifarioProcessor
from .services.pgp_processor import procesar_nota_tecnica, procesar_consumo


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
        query = (request.query_params.get('q') or '').strip()
        # Se consulta por código/descripción: sin término no se devuelve todo
        # el catálogo (pueden ser miles de filas).
        if not query:
            return Response([])
        qs = (
            DetalleTarifa.objects.filter(anexo_origen__contrato_id=pk)
            .filter(Q(codigo_cups__icontains=query) | Q(descripcion__icontains=query))
            .order_by('codigo_cups')[:100]
        )
        return Response(DetalleTarifaSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='anexos')
    def anexos(self, request, pk=None):
        anexos = AnexoTarifario.objects.filter(contrato_id=pk).order_by('-fecha_carga')
        return Response(AnexoTarifarioSerializer(anexos, many=True).data)

    @action(detail=True, methods=['get'], url_path='pgp')
    def pgp(self, request, pk=None):
        """Tablero de control PGP de un mes: techo vs ejecutado, por actividad
        y serie diaria de consumo."""
        try:
            anio = int(request.query_params.get('anio'))
            mes = int(request.query_params.get('mes'))
        except (TypeError, ValueError):
            return Response({'error': 'Parámetros "anio" y "mes" requeridos.'},
                            status=status.HTTP_400_BAD_REQUEST)

        contrato = self.get_object()
        nota = NotaTecnica.objects.filter(contrato=contrato, anio=anio, mes=mes).first()
        consumos = RegistroConsumo.objects.filter(
            contrato=contrato, fecha__year=anio, fecha__month=mes,
        )
        total_ejecutado = float(consumos.aggregate(s=Sum('valor_total'))['s'] or 0)
        techo = float(nota.valor_global) if nota else 0.0

        ejec_por_cod = {
            r['codigo']: r
            for r in consumos.values('codigo').annotate(
                valor=Sum('valor_total'), cantidad=Sum('cantidad'),
            )
        }

        actividades = []
        codigos_presupuestados = set()
        if nota:
            for l in nota.lineas.all():
                ej = ejec_por_cod.get(l.codigo, {})
                actividades.append({
                    'codigo': l.codigo,
                    'descripcion': l.descripcion,
                    'frecuencia_esperada': float(l.frecuencia_esperada),
                    'valor_presupuestado': float(l.valor_total),
                    'cantidad_ejecutada': float(ej.get('cantidad') or 0),
                    'valor_ejecutado': float(ej.get('valor') or 0),
                })
                codigos_presupuestados.add(l.codigo)
        # Consumos de códigos que no estaban en la nota técnica.
        for cod, ej in ejec_por_cod.items():
            if cod not in codigos_presupuestados:
                actividades.append({
                    'codigo': cod or '(sin código)',
                    'descripcion': '(no presupuestado)',
                    'frecuencia_esperada': 0.0,
                    'valor_presupuestado': 0.0,
                    'cantidad_ejecutada': float(ej.get('cantidad') or 0),
                    'valor_ejecutado': float(ej.get('valor') or 0),
                })

        serie = [
            {'fecha': x['fecha'], 'valor': float(x['valor'] or 0)}
            for x in consumos.values('fecha').annotate(valor=Sum('valor_total')).order_by('fecha')
        ]

        return Response({
            'anio': anio,
            'mes': mes,
            'tiene_nota': bool(nota),
            'poblacion': nota.poblacion if nota else 0,
            'techo': techo,
            'total_ejecutado': total_ejecutado,
            'saldo': techo - total_ejecutado if techo else None,
            'porcentaje_ejecucion': round(total_ejecutado / techo * 100, 1) if techo else None,
            'total_registros': consumos.count(),
            'actividades': actividades,
            'serie_diaria': serie,
        })


class NotaTecnicaViewSet(viewsets.ModelViewSet):
    queryset = NotaTecnica.objects.select_related('contrato').all()
    serializer_class = NotaTecnicaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        contrato = self.request.query_params.get('contrato')
        anio = self.request.query_params.get('anio')
        mes = self.request.query_params.get('mes')
        if contrato:
            qs = qs.filter(contrato_id=contrato)
        if anio:
            qs = qs.filter(anio=anio)
        if mes:
            qs = qs.filter(mes=mes)
        return qs

    @action(detail=True, methods=['get'], url_path='lineas')
    def lineas(self, request, pk=None):
        nota = self.get_object()
        return Response(LineaNotaTecnicaSerializer(nota.lineas.all(), many=True).data)

    @action(detail=True, methods=['post'], url_path='cargar',
            parser_classes=[MultiPartParser, FormParser])
    def cargar(self, request, pk=None):
        nota = self.get_object()
        archivo = request.FILES.get('archivo_excel')
        if not archivo:
            return Response({'error': 'Falta el archivo (archivo_excel).'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            total = procesar_nota_tecnica(nota, archivo)
        except Exception as exc:
            return Response({'error': f'No se pudo procesar el archivo: {exc}'},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        data = NotaTecnicaSerializer(nota).data
        data['lineas_procesadas'] = total
        return Response(data, status=status.HTTP_201_CREATED)


class ConsumoUploadView(APIView):
    """Carga registros de consumo (ejecución PGP) desde un Excel."""
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        from datetime import date
        contrato_id = request.data.get('contrato')
        archivo = request.FILES.get('archivo_excel')
        if not contrato_id or not archivo:
            return Response({'error': 'Se requieren "contrato" y "archivo_excel".'},
                            status=status.HTTP_400_BAD_REQUEST)
        contrato = get_object_or_404(Contrato, pk=contrato_id)

        # Fecha por defecto para filas sin fecha: primer día del mes indicado.
        fecha_defecto = None
        anio = request.data.get('anio')
        mes = request.data.get('mes')
        if anio and mes:
            try:
                fecha_defecto = date(int(anio), int(mes), 1)
            except ValueError:
                fecha_defecto = None

        try:
            total = procesar_consumo(contrato, archivo, fecha_defecto=fecha_defecto)
        except Exception as exc:
            return Response({'error': f'No se pudo procesar el archivo: {exc}'},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        return Response({'registros_procesados': total}, status=status.HTTP_201_CREATED)

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
