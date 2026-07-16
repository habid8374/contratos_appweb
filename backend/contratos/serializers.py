
from rest_framework import serializers
from .models import Contrato, Administradora, AnexoTarifario, DetalleTarifa, AlertaContrato


class AdministradoraSerializer(serializers.ModelSerializer):
    regimen_display = serializers.CharField(source='get_regimen_display', read_only=True)
    total_contratos = serializers.IntegerField(source='contratos.count', read_only=True)

    class Meta:
        model = Administradora
        fields = [
            'id', 'nombre', 'nit', 'regimen', 'regimen_display',
            'ciudad', 'departamento', 'codigo_postal', 'correo', 'total_contratos',
        ]


class AlertaContratoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertaContrato
        fields = ['dias_previos', 'activa', 'ultima_notificacion_enviada']
        read_only_fields = ['ultima_notificacion_enviada']


class ContratoBusquedaSerializer(serializers.ModelSerializer):
    administradora = AdministradoraSerializer(read_only=True)
    regimen_estimado = serializers.SerializerMethodField()

    class Meta:
        model = Contrato
        fields = ['id', 'numero_contrato', 'administradora', 'modalidad', 'fecha_fin', 'estado', 'regimen_estimado']

    def get_regimen_estimado(self, obj):
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
    alerta = AlertaContratoSerializer(read_only=True)
    dias_para_vencer = serializers.SerializerMethodField()

    class Meta:
        model = Contrato
        fields = [
            'id', 'numero_contrato', 'administradora', 'modalidad', 'objeto',
            'fecha_inicio', 'fecha_fin', 'valor_total', 'manual_referencia',
            'porcentaje_negociado', 'estado', 'documento_negociacion', 'alerta',
            'dias_para_vencer',
        ]

    def get_dias_para_vencer(self, obj):
        from datetime import date
        if not obj.fecha_fin:
            return None
        return (obj.fecha_fin - date.today()).days


class ContratoEscrituraSerializer(serializers.ModelSerializer):
    """Crear / editar contratos, con la alerta anidada."""
    alerta = AlertaContratoSerializer(required=False)

    class Meta:
        model = Contrato
        fields = [
            'id', 'numero_contrato', 'administradora', 'modalidad', 'objeto',
            'fecha_inicio', 'fecha_fin', 'valor_total', 'manual_referencia',
            'porcentaje_negociado', 'estado', 'documento_negociacion', 'alerta',
        ]

    def create(self, validated_data):
        alerta_data = validated_data.pop('alerta', None)
        contrato = Contrato.objects.create(**validated_data)
        if alerta_data:
            AlertaContrato.objects.create(contrato=contrato, **alerta_data)
        return contrato

    def update(self, instance, validated_data):
        alerta_data = validated_data.pop('alerta', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if alerta_data is not None:
            AlertaContrato.objects.update_or_create(contrato=instance, defaults=alerta_data)
        return instance


class DetalleTarifaSerializer(serializers.ModelSerializer):
    tipo_tecnologia_display = serializers.CharField(source='get_tipo_tecnologia_display', read_only=True)

    class Meta:
        model = DetalleTarifa
        fields = [
            'id', 'hoja', 'codigo_cups', 'descripcion', 'tipo_tecnologia', 'tipo_tecnologia_display',
            'esta_incluido', 'manual_referencia', 'tarifa_base', 'porcentaje_pactado', 'valor_final',
        ]


class AnexoTarifarioSerializer(serializers.ModelSerializer):
    total_detalles = serializers.IntegerField(source='detalles.count', read_only=True)

    class Meta:
        model = AnexoTarifario
        fields = ['id', 'contrato', 'nombre_anexo', 'archivo_excel', 'fecha_carga', 'total_detalles']
        read_only_fields = ['fecha_carga']
