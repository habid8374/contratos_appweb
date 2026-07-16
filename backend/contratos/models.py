
import os
from datetime import date, timedelta
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def anexo_upload_path(instance, filename):
    # Guarda el archivo en una carpeta con el ID del contrato para mantener el orden
    return f'contratos/{instance.contrato.id}/anexos/{filename}'

def negociacion_upload_path(instance, filename):
    return f'contratos/{instance.id or "nuevo"}/negociacion/{filename}'

class Administradora(models.Model):
    class Regimen(models.TextChoices):
        SUBSIDIADO = 'SUB', _('Subsidiado')
        CONTRIBUTIVO = 'CON', _('Contributivo')
        AMBOS = 'AMB', _('Ambos')
        OTRO = 'OTR', _('Otro')

    nombre = models.CharField(max_length=255, unique=True, db_index=True)
    nit = models.CharField(max_length=20, unique=True)
    regimen = models.CharField(
        max_length=3,
        choices=Regimen.choices,
        default=Regimen.OTRO,
        help_text='Régimen que administra la EAPB/EPS (un mismo NIT puede manejar ambos).',
    )
    ciudad = models.CharField(max_length=120, blank=True)
    departamento = models.CharField(max_length=120, blank=True)
    codigo_postal = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(blank=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class Contrato(models.Model):
    class Modalidad(models.TextChoices):
        EVENTO = 'EV', _('Evento')
        CAPITACION = 'CAP', _('Capitación')
        PGP = 'PGP', _('Paquete de Gestión Global (PGP)')

    class Estado(models.TextChoices):
        ACTIVO = 'ACT', _('Activo')
        INACTIVO = 'INA', _('Inactivo')

    numero_contrato = models.CharField(max_length=100, unique=True, db_index=True)
    administradora = models.ForeignKey(Administradora, on_delete=models.PROTECT, related_name='contratos')
    modalidad = models.CharField(max_length=3, choices=Modalidad.choices, default=Modalidad.EVENTO)
    objeto = models.TextField(blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    valor_total = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    manual_referencia = models.CharField(
        max_length=120, blank=True, default='',
        help_text='Manual tarifario base, p. ej. ISS 2001, SOAT, Propio.',
    )
    porcentaje_negociado = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        help_text='Porcentaje pactado sobre el manual (p. ej. 35.00 para +35%).',
    )
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.ACTIVO)
    documento_negociacion = models.FileField(
        upload_to=negociacion_upload_path, null=True, blank=True,
        help_text='PDF de la negociación del contrato.',
    )

    class Meta:
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.numero_contrato} - {self.administradora.nombre}"

class AlertaContrato(models.Model):
    contrato = models.OneToOneField(Contrato, on_delete=models.CASCADE, related_name='alerta')
    dias_previos = models.PositiveIntegerField(default=90, help_text="Días previos para generar la alerta antes del vencimiento.")
    activa = models.BooleanField(default=True)
    ultima_notificacion_enviada = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Alerta para {self.contrato.numero_contrato} a {self.dias_previos} días."

class AnexoTarifario(models.Model):
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='anexos')
    nombre_anexo = models.CharField(max_length=255)
    archivo_excel = models.FileField(upload_to=anexo_upload_path)
    fecha_carga = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_anexo} ({self.contrato.numero_contrato})"

class DetalleTarifa(models.Model):
    class TipoTecnologia(models.TextChoices):
        PROCEDIMIENTO = 'P', _('Procedimiento')
        MEDICAMENTO = 'M', _('Medicamento')
        INSUMO = 'I', _('Insumo')

    anexo_origen = models.ForeignKey(AnexoTarifario, on_delete=models.CASCADE, related_name='detalles')
    hoja = models.CharField(max_length=120, blank=True, default='', db_index=True,
                            help_text='Hoja del Excel de la que provino la fila.')
    codigo_cups = models.CharField(max_length=60, db_index=True)
    descripcion = models.CharField(max_length=500, blank=True, default='')
    tipo_tecnologia = models.CharField(max_length=1, choices=TipoTecnologia.choices,
                                       default=TipoTecnologia.PROCEDIMIENTO)
    esta_incluido = models.BooleanField(default=True)
    manual_referencia = models.CharField(max_length=120, blank=True, default='')
    tarifa_base = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    porcentaje_pactado = models.DecimalField(max_digits=6, decimal_places=2, default=0.0)
    valor_final = models.DecimalField(max_digits=16, decimal_places=2, editable=False, default=0)

    @staticmethod
    def computar_valor_final(tarifa_base, porcentaje_pactado):
        from decimal import Decimal
        tb = Decimal(str(tarifa_base or 0))
        pp = Decimal(str(porcentaje_pactado or 0))
        return tb * (1 + pp / Decimal('100'))

    def save(self, *args, **kwargs):
        self.valor_final = self.computar_valor_final(self.tarifa_base, self.porcentaje_pactado)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_cups} - {self.descripcion}"

    class Meta:
        ordering = ['hoja', 'codigo_cups']


# ---------------------------------------------------------------------------
# Módulo PGP (Pago Global Prospectivo): nota técnica y control de consumo
# ---------------------------------------------------------------------------

class NotaTecnica(models.Model):
    """Presupuesto mensual de un contrato PGP, según la nota técnica pactada."""
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='notas_tecnicas')
    anio = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField(help_text='1 = enero … 12 = diciembre.')
    poblacion = models.PositiveIntegerField(default=0, help_text='Afiliados cubiertos en el mes.')
    valor_global = models.DecimalField(
        max_digits=18, decimal_places=2, default=0,
        help_text='Techo presupuestal del mes (valor global del PGP).',
    )
    observaciones = models.TextField(blank=True, default='')
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('contrato', 'anio', 'mes')
        ordering = ['-anio', '-mes']

    def __str__(self):
        return f"Nota técnica {self.contrato.numero_contrato} {self.mes:02d}/{self.anio}"


class LineaNotaTecnica(models.Model):
    """Actividad presupuestada dentro de una nota técnica."""
    nota_tecnica = models.ForeignKey(NotaTecnica, on_delete=models.CASCADE, related_name='lineas')
    codigo = models.CharField(max_length=60, db_index=True)
    descripcion = models.CharField(max_length=500, blank=True, default='')
    frecuencia_esperada = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_unitario = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} ({self.nota_tecnica_id})"


class RegistroConsumo(models.Model):
    """Servicio realmente prestado (ejecución) de un contrato PGP."""
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='consumos')
    fecha = models.DateField(db_index=True)
    codigo = models.CharField(max_length=60, db_index=True, blank=True, default='')
    descripcion = models.CharField(max_length=500, blank=True, default='')
    cantidad = models.DecimalField(max_digits=14, decimal_places=2, default=1)
    valor_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return f"{self.fecha} {self.codigo} ({self.contrato_id})"
