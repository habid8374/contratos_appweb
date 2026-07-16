
from rest_framework import serializers
from .models import Contrato, Administradora, AnexoTarifario, DetalleTarifa


class AdministradoraSerializer(serializers.ModelSerializer):
    regimen_display = serializers.CharField(source='get_regimen_display', read_only=True)

    class Meta:
        model = Administradora
        fields = ['nombre', 'nit', 'regimen', 'regimen_display']


class ContratoBusquedaSerializer(serializers.ModelSerializer):
    administradora = AdministradoraSerializer(read_only=True)
    regimen_estimado = serializers.SerializerMethodField()

    class Meta:
        model = Contrato
        fields = ['id', 'numero_contrato', 'administradora', 'modalidad', 'fecha_fin', 'estado', 'regimen_estimado']

    def get_regimen_estimado(self, obj):
        # Preferir el campo real del régimen; si no está definido, caer a heurística.
        if obj.administradora.regimen and obj.administradora.regimen != Administradora.Regimen.OTRO:
            return obj.administradora.get_regimen_display()
        nombre_admin = obj.administradora.nombre.lower()
        if 'subsidiado' in nombre_admin:
            return 'Subsidiado'
        if 'contributivo' in nombre_admin:
            return 'Contributivo'
        return 'No identificado'


class ContratoDetalleSerializer(serializers.ModelSerializer):
    administradora = AdministradoraSerializer(read_only=True)

    class Meta:
        model = Contrato
        fields = [
            'id',
            'numero_contrato',
            'administradora',
            'modalidad',
            'objeto',
            'fecha_inicio',
            'fecha_fin',
            'valor_total',
            'estado',
        ]


class DetalleTarifaSerializer(serializers.ModelSerializer):
    tipo_tecnologia_display = serializers.CharField(source='get_tipo_tecnologia_display', read_only=True)

    class Meta:
        model = DetalleTarifa
        fields = [
            'id',
            'codigo_cups',
            'descripcion',
            'tipo_tecnologia',
            'tipo_tecnologia_display',
            'esta_incluido',
            'manual_referencia',
            'tarifa_base',
            'porcentaje_pactado',
            'valor_final',
        ]


class AnexoTarifarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnexoTarifario
        fields = ['id', 'contrato', 'nombre_anexo', 'archivo_excel', 'fecha_carga']
        read_only_fields = ['fecha_carga']
