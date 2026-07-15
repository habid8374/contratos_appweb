
from rest_framework import serializers
from .models import Contrato, Administradora


class AdministradoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administradora
        fields = ['nombre', 'nit']


class ContratoBusquedaSerializer(serializers.ModelSerializer):
    administradora = AdministradoraSerializer(read_only=True)
    regimen_estimado = serializers.SerializerMethodField()

    class Meta:
        model = Contrato
        fields = ['id', 'numero_contrato', 'administradora', 'modalidad', 'fecha_fin', 'estado', 'regimen_estimado']

    def get_regimen_estimado(self, obj):
        nombre_admin = obj.administradora.nombre.lower()
        if 'subsidiado' in nombre_admin:
            return 'Subsidiado'
        if 'contributivo' in nombre_admin:
            return 'Contributivo'
        if obj.modalidad == 'EV':
            return 'Evento'
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
